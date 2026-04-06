from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER, DEAD_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types
from ryu.topology import event as topo_event
from ryu.topology.api import get_switch, get_link
import networkx as nx
import time
import json
import threading

from app import launch_dashboard

class LinkFailureController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.topology = nx.Graph()
        self.datapaths = {}
        self.mac_to_port = {}
        self.event_log = []
        self.lock = threading.Lock()
        from app import launch_dashboard
        launch_dashboard(self)

    def log_event(self, etype, msg, recovery_ms=None):
        entry = {
            "time": time.strftime("%H:%M:%S"),
            "type": etype,
            "msg": msg,
            "recovery_ms": recovery_ms
        }
        with self.lock:
            self.event_log.append(entry)
            if len(self.event_log) > 100:
                self.event_log.pop(0)

    def get_events(self):
        with self.lock:
            return list(self.event_log)

    def get_topology_data(self):
        switches = get_switch(self, None)
        links = get_link(self, None)
        nodes = [{"id": s.dp.id} for s in switches]
        edges = [{"source": l.src.dpid, "target": l.dst.dpid,
                  "src_port": l.src.port_no, "dst_port": l.dst.port_no} for l in links]
        return {"nodes": nodes, "edges": edges}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        dp = ev.msg.datapath
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER)]
        self.add_flow(dp, 0, match, actions)

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def state_change_handler(self, ev):
        dp = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            self.datapaths[dp.id] = dp
            self.log_event("SWITCH", f"Switch {dp.id} connected")
        elif ev.state == DEAD_DISPATCHER:
            self.datapaths.pop(dp.id, None)
            self.log_event("SWITCH", f"Switch {dp.id} disconnected")

    @set_ev_cls(topo_event.EventLinkAdd)
    def link_add_handler(self, ev):
        l = ev.link
        self.topology.add_edge(l.src.dpid, l.dst.dpid,
                               src_port=l.src.port_no, dst_port=l.dst.port_no)
        self.log_event("LINK_UP", f"Link up: s{l.src.dpid} <-> s{l.dst.dpid}")

    @set_ev_cls(topo_event.EventLinkDelete)
    def link_delete_handler(self, ev):
        l = ev.link
        start = time.time()
        self.log_event("LINK_DOWN", f"Link DOWN: s{l.src.dpid} <-> s{l.dst.dpid}")
        if self.topology.has_edge(l.src.dpid, l.dst.dpid):
            self.topology.remove_edge(l.src.dpid, l.dst.dpid)
        self._reroute_all(l.src.dpid, l.dst.dpid, start)

    def _reroute_all(self, failed_src, failed_dst, start_time):
        recovered = 0
        for dp_id, dp in self.datapaths.items():
            self._clear_flows(dp)
        for dp_id, dp in self.datapaths.items():
            self._install_paths(dp)
            recovered += 1
        ms = round((time.time() - start_time) * 1000, 2)
        self.log_event("RECOVERY", f"Rerouted around s{failed_src}<->s{failed_dst} ({recovered} switches updated)", recovery_ms=ms)

    def _clear_flows(self, dp):
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        match = parser.OFPMatch()
        mod = parser.OFPFlowMod(datapath=dp, command=ofp.OFPFC_DELETE,
                                out_port=ofp.OFPP_ANY, out_group=ofp.OFPG_ANY,
                                match=match, priority=1)
        dp.send_msg(mod)

    def _install_paths(self, dp):
        # reinstall table-miss so learning continues
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER)]
        self.add_flow(dp, 0, match, actions)

    def add_flow(self, dp, priority, match, actions, idle=0, hard=0):
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=dp, priority=priority,
                                idle_timeout=idle, hard_timeout=hard,
                                match=match, instructions=inst)
        dp.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dst, src = eth.dst, eth.src
        dpid = dp.id
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src] = in_port

        out_port = self.mac_to_port[dpid].get(dst, ofp.OFPP_FLOOD)
        actions = [parser.OFPActionOutput(out_port)]

        if out_port != ofp.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            self.add_flow(dp, 1, match, actions, idle=10)

        data = msg.data if msg.buffer_id == ofp.OFP_NO_BUFFER else None
        out = parser.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        dp.send_msg(out)