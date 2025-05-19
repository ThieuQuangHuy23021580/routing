####################################################
# DVrouter.py
# Name:
# HUID:
#####################################################

import json
from router import Router
from packet import Packet


class DVrouter(Router):
    """Distance vector routing protocol implementation.

    Add your own class fields and initialization code (e.g. to create forwarding table
    data structures). See the `Router` base class for docstrings of the methods to
    override.
    """

    def __init__(self, addr, heartbeat_time):
        Router.__init__(self, addr)
        self.heartbeat_time = heartbeat_time
        self.last_time = 0
        self.dv_table = {}
        self.dv_table[self.addr] = {'next_hop': None, 'cost': 0}
        self.port_info = {}
        self.forwarding_table = {}

    def handle_packet(self, port, packet):
        """Process incoming packet."""
        if packet.is_traceroute:
            if packet.dst_addr in self.forwarding_table:
                self.send(self.forwarding_table[packet.dst_addr], packet)
        else:
            try:
                dv_data = json.loads(packet.content)
                neighbor_addr = dv_data['addr']
                neighbor_dv = dv_data['dv']
                self.update_distance_vector(neighbor_addr, neighbor_dv)
            except (json.JSONDecodeError, KeyError):
                pass

    def handle_new_link(self, port, endpoint, cost):
        """Handle new link."""
        self.port_info[port] = {'addr': endpoint, 'cost': cost}
        self.dv_table[endpoint] = {'next_hop': endpoint, 'cost': cost}
        self.update_forwarding_table()
        self.broadcast_distance_vector()

    def handle_remove_link(self, port):
        """Handle removed link."""
        if port in self.port_info:
            neighbor_addr = self.port_info[port]['addr']
            del self.port_info[port]
            routes_to_remove = []
            for dest, info in self.dv_table.items():
                if info['next_hop'] == neighbor_addr:
                    routes_to_remove.append(dest)
            for dest in routes_to_remove:
                del self.dv_table[dest]
            self.update_forwarding_table()
            self.broadcast_distance_vector()

    def handle_time(self, time_ms):
        """Handle current time."""
        if time_ms - self.last_time >= self.heartbeat_time:
            self.last_time = time_ms
            self.broadcast_distance_vector()

    def update_distance_vector(self, neighbor_addr, neighbor_dv):
        """Update our distance vector based on neighbor's information."""
        neighbor_cost = None
        for port, info in self.port_info.items():
            if info['addr'] == neighbor_addr:
                neighbor_cost = info['cost']
                break
        if neighbor_cost is None:
            return
        for dest, cost in neighbor_dv.items():
            if dest == neighbor_addr:
                continue
            new_cost = neighbor_cost + cost
            if dest not in self.dv_table or new_cost < self.dv_table[dest]['cost']:
                self.dv_table[dest] = {'next_hop': neighbor_addr, 'cost': new_cost}
        self.update_forwarding_table()

    def update_forwarding_table(self):
        """Update forwarding table based on distance vector."""
        self.forwarding_table = {}
        for dest, info in self.dv_table.items():
            if dest != self.addr:
                next_hop = info['next_hop']
                for port, port_data in self.port_info.items():
                    if port_data['addr'] == next_hop:
                        self.forwarding_table[dest] = port
                        break

    def broadcast_distance_vector(self):
        """Broadcast our distance vector to all neighbors."""
        if not self.port_info:
            return
        dv_data = {
            'addr': self.addr,
            'dv': {dest: info['cost'] for dest, info in self.dv_table.items()}
        }
        packet = Packet(dst_addr=None, src_addr=self.addr, content=json.dumps(dv_data), is_routing=True)
        for port in self.port_info:
            self.send(port, packet)

    def __repr__(self):
        """Representation for debugging in the network visualizer."""
        return f"DVrouter(addr={self.addr}, links={list(self.port_info.items())}, dv={self.dv_table}, ft={self.forwarding_table})"
