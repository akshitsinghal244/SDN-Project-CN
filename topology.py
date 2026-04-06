from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.topo import Topo
from mininet.log import setLogLevel
from mininet.cli import CLI
import time

class DiamondTopo(Topo):

    def build(self):
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')

        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')
        s4 = self.addSwitch('s4')

        self.addLink(h1, s1)
        self.addLink(s1, s2)
        self.addLink(s1, s3)
        self.addLink(s2, s4)
        self.addLink(s3, s4)
        self.addLink(s4, h2)

if __name__ == '__main__':
    setLogLevel('info')

    topo = DiamondTopo()
    net = Mininet(topo=topo, controller=None)
    net.addController('c0', controller=RemoteController,
                      ip='127.0.0.1', port=6633)
    net.start()

    print("\n*** Network started")
    print("*** Topology: h1 - s1 - s2/s3 - s4 - h2")
    print("*** Two paths: s1->s2->s4 and s1->s3->s4")
    print("\n*** Testing connectivity...")
    net.pingAll()

    print("\n*** Simulating link failure: s1 <-> s2")
    print("*** Watch the dashboard at http://localhost:5000")
    time.sleep(3)
    net.configLinkStatus('s1', 's2', 'down')

    print("*** Link s1<->s2 is DOWN — controller should reroute via s3")
    time.sleep(5)

    print("\n*** Restoring link s1 <-> s2")
    net.configLinkStatus('s1', 's2', 'up')
    print("*** Link restored")
    time.sleep(3)

    print("\n*** Dropping into Mininet CLI — type 'exit' to quit")
    print("*** Tip: run 'link s1 s3 down' to simulate another failure")
    CLI(net)

    net.stop()