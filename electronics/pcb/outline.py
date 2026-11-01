"""Shallow annular wall segment, millimetres in the KiCad coordinate frame.

Outer R141 fits nominal R146 bore with 5 mm radial allowance; inner R91
leaves 6.15 mm beyond the circumscribed radius of a centred 120 mm square fan.
These are 2D assumptions, not a housing/post/sink fit validation.
"""
import math
CX,CY=-41.,90.
OUTER,INNER=141.,91.
HALF_HEIGHT,FILLET=40.,2.
YTOP,YBOTTOM=CY-HALF_HEIGHT,CY+HALF_HEIGHT
dy=HALF_HEIGHT-FILLET
IX=CX+math.sqrt((INNER+FILLET)**2-dy**2)
OX=CX+math.sqrt((OUTER-FILLET)**2-dy**2)
XMIN=IX-FILLET
XMAX=CX+OUTER
ORIGIN=(XMIN,YBOTTOM)
def tangent(radius,offset_radius,x,y):
    return (CX+(x-CX)*radius/offset_radius,CY+(y-CY)*radius/offset_radius)
IT=tangent(INNER,INNER+FILLET,IX,YTOP+FILLET)
IB=tangent(INNER,INNER+FILLET,IX,YBOTTOM-FILLET)
OT=tangent(OUTER,OUTER-FILLET,OX,YTOP+FILLET)
OB=tangent(OUTER,OUTER-FILLET,OX,YBOTTOM-FILLET)
def arc_mid(center,a,b):
    aa=math.atan2(a[1]-center[1],a[0]-center[0]);bb=math.atan2(b[1]-center[1],b[0]-center[0])
    delta=(bb-aa+math.pi)%(2*math.pi)-math.pi
    r=math.dist(center,a);angle=aa+delta/2
    return center[0]+r*math.cos(angle),center[1]+r*math.sin(angle)
LINES=[((IX,YTOP),(OX,YTOP)),((OX,YBOTTOM),(IX,YBOTTOM))]
ARCS=[
    ((OX,YTOP),arc_mid((OX,YTOP+FILLET),(OX,YTOP),OT),OT),
    (OT,(XMAX,CY),OB),
    (OB,arc_mid((OX,YBOTTOM-FILLET),OB,(OX,YBOTTOM)),(OX,YBOTTOM)),
    ((IX,YBOTTOM),arc_mid((IX,YBOTTOM-FILLET),(IX,YBOTTOM),IB),IB),
    (IB,(CX+INNER,CY),IT),
    (IT,arc_mid((IX,YTOP+FILLET),IT,(IX,YTOP)),(IX,YTOP)),
]
