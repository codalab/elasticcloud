from elasticcloud import ElasticCloud

c = ElasticCloud("GCE")
ips = c.cloud.get_node_ips()
names = c.cloud.get_node_names()

for ip, name in zip(ips, names):
    print(name, ip[0])

print('Expanding...')
c.expand()
print('Expanding...')
c.expand()
print('Expanding...')
c.expand()
print('Number of instances:', c.cloud.get_active_node_quantity())

print('Number of instances:', c.cloud.get_active_node_quantity())
print('Shrinking...')
c.shrink()
print('Shrinking...')
c.shrink()
print(c.cloud.get_oldest_node())
print('Number of instances:', c.cloud.get_active_node_quantity())
