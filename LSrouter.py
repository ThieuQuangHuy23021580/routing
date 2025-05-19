####################################################
# LSrouter.py
# Name:
# HUID:
#####################################################

import json
from router import Router
from packet import Packet


class LSrouter(Router):
    """Link state routing protocol implementation.

    Add your own class fields and initialization code (e.g. to create forwarding table
    data structures). See the `Router` base class for docstrings of the methods to
    override.
    """

    def __init__(self, addr, heartbeat_time):
        Router.__init__(self, addr)
        self.heartbeat_time = heartbeat_time
        self.last_time = 0
        self.ls_db = {}
        self.ls_db[self.addr] = {'links': {}, 'seq': 0}
        self.forwarding_table = {}
        self.port_to_addr = {}
        self.seen_links = set()

    def handle_packet(self, port, packet):
        """Process incoming packet."""
        if packet.is_traceroute:
            if packet.dst_addr in self.forwarding_table:
                self.send(self.forwarding_table[packet.dst_addr], packet)
        else:
            try:
                ls_data = json.loads(packet.content)
                source_addr = ls_data['addr']
                seq_num = ls_data['seq']
                links = ls_data['links']
                
                if (source_addr not in self.ls_db) or (seq_num > self.ls_db[source_addr]['seq']):
                    self.ls_db[source_addr] = {'links': links, 'seq': seq_num}
                    self.compute_shortest_paths()
                    for neighbor_port in self.links:
                        if neighbor_port != port:
                            self.send(neighbor_port, packet)
            except (json.JSONDecodeError, KeyError):
                pass

    def handle_new_link(self, port, endpoint, cost):
        """Handle new link."""
        self.port_to_addr[port] = endpoint
        self.ls_db[self.addr]['links'][endpoint] = cost
        self.ls_db[self.addr]['seq'] += 1
        self.compute_shortest_paths()
        self.broadcast_link_state()

    def handle_remove_link(self, port):
        """Handle removed link."""
        if port in self.port_to_addr:
            endpoint = self.port_to_addr[port]
            del self.port_to_addr[port]
            if endpoint in self.ls_db[self.addr]['links']:
                del self.ls_db[self.addr]['links'][endpoint]
            self.ls_db[self.addr]['seq'] += 1
            self.compute_shortest_paths()
            self.broadcast_link_state()

    def handle_time(self, time_ms):
        """Handle current time."""
        if time_ms - self.last_time >= self.heartbeat_time:
            self.last_time = time_ms
            self.broadcast_link_state()

    def broadcast_link_state(self):
        """Broadcast this router's link state to all neighbors."""
        if not self.links:
            return
        
        ls_data = {
            'addr': self.addr,
            'seq': self.ls_db[self.addr]['seq'],
            'links': self.ls_db[self.addr]['links']
        }
        
        packet = Packet(dst_addr=None, src_addr=self.addr, content=json.dumps(ls_data), is_routing=True)
        
        for port in self.links:
            self.send(port, packet)

    def compute_shortest_paths(self):
        """Compute shortest paths using Dijkstra's algorithm."""
        graph = {}
        for router, data in self.ls_db.items():
            if router not in graph:
                graph[router] = {}
            for neighbor, cost in data['links'].items():
                if neighbor in graph:
                    graph[router][neighbor] = cost
                else:
                    graph[router][neighbor] = cost
                    graph[neighbor] = {}
        
        distances = {node: float('infinity') for node in graph}
        previous = {node: None for node in graph}
        distances[self.addr] = 0
        unvisited = list(graph.keys())
        
        while unvisited:
            current = min(unvisited, key=lambda node: distances[node])
            
            if distances[current] == float('infinity'):
                break
                
            unvisited.remove(current)
            
            for neighbor, cost in graph[current].items():
                if neighbor not in graph:
                    continue
                    
                distance = distances[current] + cost
                
                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    previous[neighbor] = current
        
        self.forwarding_table = {}
        
        for dest in graph:
            if dest != self.addr:
                next_hop = dest
                while previous[next_hop] != self.addr and previous[next_hop] is not None:
                    next_hop = previous[next_hop]
                
                if previous[next_hop] == self.addr:
                    for port, addr in self.port_to_addr.items():
                        if addr == next_hop:
                            self.forwarding_table[dest] = port
                            break

    def __repr__(self):
        """Representation for debugging in the network visualizer."""
        return f"LSrouter(addr={self.addr}, links={list(self.port_to_addr.items())}, ft={self.forwarding_table})"
