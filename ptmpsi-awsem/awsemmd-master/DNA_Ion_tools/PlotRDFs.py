import sys
from pylab import *

filename=sys.argv[1]

cols=[]
for iarg in sys.argv[2:]:
	cols.append(int(iarg))

y=[]
for i in range(0,len(cols)):
	y.append([])

x=[]

file=open(filename, 'r')

for l in file:
	if l[0]=='#': continue
	l = l.strip().split()
	
	if len(l)>2:
		if float(l[1])>20: break
		x.append(float(l[1]))
		for i in range(0,len(cols)):
			icol=cols[i]
			y[i].append(float(l[icol+1]))

file.close()

figure()
for iy in y:
	plot(x, iy, linewidth=1.0)

xlabel('r')
ylabel('RDF')
title('Plot of Radial Distribution Function')
grid(True)
show()
