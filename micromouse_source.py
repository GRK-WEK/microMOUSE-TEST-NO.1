import math
import cadquery as cq

V = cq.Vector

# ---------------- global parameters (mm) ----------------
PCB_T      = 1.6
PCB_BOT    = 16.5            # underside of PCB above floor
PCB_TOP    = PCB_BOT + PCB_T # 18.1
AXLE_Z     = 11.0            # wheel radius
WHEEL_R    = 11.0
WHEEL_W    = 8.0
WHEEL_CX   = 36.0            # wheel centre x  (overall width = 2*36+8 = 80 mm)
FAN_Y      = -28.0
SKIRT_BOT  = 1.0

def box(cx, cy, cz, dx, dy, dz):
    return cq.Workplane("XY").box(dx, dy, dz).translate((cx, cy, cz))

def cyl_x(x0, x1, y, z, r):
    """cylinder along X from x0..x1"""
    return (cq.Workplane("YZ").workplane(offset=x0).center(y, z)
            .circle(r).extrude(x1 - x0))

def cyl_z(cx, cy, z0, z1, r):
    return cq.Workplane("XY").workplane(offset=z0).center(cx, cy).circle(r).extrude(z1 - z0)

parts = []   # (name, shape, (r,g,b))
def add(name, shape, rgb, a=1.0):
    parts.append((name, shape, cq.Color(rgb[0], rgb[1], rgb[2], a)))

BLACK  = (0.06, 0.06, 0.07)
RED    = (0.85, 0.07, 0.07)
GOLD   = (0.85, 0.65, 0.13)
SILVER = (0.75, 0.76, 0.78)
DGREY  = (0.20, 0.21, 0.23)
ALU    = (0.60, 0.62, 0.66)

# ---------------- PCB chassis ----------------
pts = [(-22, 48), (22, 48), (31, 36), (31, -44), (27, -48),
       (-27, -48), (-31, -44), (-31, 36)]
pcb = (cq.Workplane("XY").workplane(offset=PCB_BOT)
       .polyline(pts).close().extrude(PCB_T))
pcb = pcb.edges("|Z").fillet(1.5)
pcb = pcb.cut(cyl_z(0, FAN_Y, PCB_BOT - 1, PCB_TOP + 1, 14.0))       # fan intake
for sx in (-1, 1):                                                   # lightening slots
    slot = (cq.Workplane("XY").workplane(offset=PCB_BOT - 1)
            .center(sx * 22, 2).slot2D(16, 4, 90).extrude(PCB_T + 2))
    pcb = pcb.cut(slot)
add("PCB_Chassis", pcb, BLACK)

# ---------------- wheels ----------------
def wheel(side):
    xc = side * WHEEL_CX
    x0 = xc - WHEEL_W / 2
    tire = (cq.Workplane("YZ").workplane(offset=x0).center(0, AXLE_Z)
            .circle(WHEEL_R).extrude(WHEEL_W))
    tire = tire.faces(">X or <X").edges().fillet(1.6)
    tire = tire.cut(cyl_x(x0 - 1, x0 + WHEEL_W + 1, 0, AXLE_Z, 7.6))
    hub = cyl_x(x0, x0 + WHEEL_W, 0, AXLE_Z, 7.6)
    holes = (cq.Workplane("YZ").workplane(offset=x0 - 1).center(0, AXLE_Z)
             .polarArray(4.9, 0, 360, 5).circle(1.7).extrude(WHEEL_W + 2))
    hub = hub.cut(holes).cut(cyl_x(x0 - 1, x0 + WHEEL_W + 1, 0, AXLE_Z, 1.5))
    return tire, hub

for side, tag in ((-1, "L"), (1, "R")):
    tire, hub = wheel(side)
    add(f"Wheel_Tire_{tag}", tire, BLACK)
    add(f"Wheel_Hub_{tag}", hub, RED)

# ---------------- N20 gearmotors + encoders ----------------
def n20(side):
    s = side
    xo = s * 30.5                        # outer gearbox face
    inw = -s                             # direction toward centre is -s*... (x decreases for +side)
    # gearbox 9mm, can 15mm, both 12(y) x 10(z)
    gb_a, gb_b = sorted((xo, xo + inw * 9))
    can_a, can_b = sorted((xo + inw * 9, xo + inw * 24))
    gb  = box((gb_a + gb_b) / 2, 0, AXLE_Z, 9, 12, 10).edges("|X").fillet(0.8)
    can = cyl_x(can_a, can_b, 0, AXLE_Z, 6.0).intersect(
        box((can_a + can_b) / 2, 0, AXLE_Z, 15, 12, 10))
    # output shaft 3mm (reaches wheel hub) + rear shaft
    sh_a, sh_b = sorted((xo, s * 39.6))
    shaft = cyl_x(sh_a, sh_b, 0, AXLE_Z, 1.5)
    end = xo + inw * 24
    r_a, r_b = sorted((end, end + inw * 3))
    rear = cyl_x(r_a, r_b, 0, AXLE_Z, 0.75)
    m_a, m_b = sorted((end + inw * 0.5, end + inw * 3))
    mag = cyl_x(m_a, m_b, 0, AXLE_Z, 3.0)
    # encoder board hugging the magnet, tied to the PCB underside
    eb_x = end + inw * 4.2
    enc = box(eb_x, 0, (6.0 + PCB_BOT) / 2, 0.8, 8.0, PCB_BOT - 6.0)
    chip = box(eb_x - inw * 0.7, 0, AXLE_Z, 0.6, 3.0, 3.0)
    return gb, can, shaft, rear, mag, enc, chip

for side, tag in ((-1, "L"), (1, "R")):
    gb, can, shaft, rear, mag, enc, chip = n20(side)
    add(f"Motor_Gearbox_{tag}", gb, ALU)
    add(f"Motor_Can_{tag}", can, SILVER)
    add(f"Motor_Shaft_{tag}", shaft.union(rear), (0.9, 0.9, 0.92))
    add(f"Encoder_Magnet_{tag}", mag, (0.3, 0.3, 0.35))
    add(f"Encoder_PCB_{tag}", enc, BLACK)
    add(f"Encoder_Chip_{tag}", chip, GOLD)

# motor cradles (3D-printed, carbon-nylon)
for side, tag in ((-1, "L"), (1, "R")):
    xa, xb = sorted((side * 29.5, side * 8.0))
    cr = box((xa + xb) / 2, 0, (3.8 + PCB_BOT) / 2, xb - xa, 16, PCB_BOT - 3.8)
    cr = cr.cut(box((xa + xb) / 2, 0, (5.9 + PCB_BOT + 1) / 2, xb - xa + 2, 12.2, PCB_BOT + 1 - 5.9))
    add(f"Motor_Cradle_{tag}", cr, DGREY)

# ---------------- front skids ----------------
for sx, tag in ((-1, "L"), (1, "R")):
    x, y = sx * 14, 42
    body = cyl_z(x, y, 3.3, PCB_BOT, 2.5)
    tip = cq.Workplane("XY").add(cq.Solid.makeSphere(2.5, V(x, y, 3.3), V(0, 0, -1), 0, 90, 360))
    add(f"Skid_{tag}", body.union(tip), (0.95, 0.95, 0.95))

# ---------------- fan + skirt ----------------
skirt = cyl_z(0, FAN_Y, SKIRT_BOT, PCB_BOT, 18.0).cut(cyl_z(0, FAN_Y, SKIRT_BOT - 1, PCB_BOT + 1, 16.5))
add("Fan_Skirt", skirt, BLACK, 0.85)
ret = cyl_z(0, FAN_Y, 13.0, PCB_BOT, 19.0).cut(cyl_z(0, FAN_Y, 12, PCB_BOT + 1, 18.0))
add("Fan_Skirt_Retainer", ret, DGREY)

FZ0, FZ1 = PCB_TOP, PCB_TOP + 9
shroud = cyl_z(0, FAN_Y, FZ0, FZ1, 16.0).cut(cyl_z(0, FAN_Y, FZ0 - 1, FZ1 + 1, 14.0))
shroud = shroud.faces(">Z").edges().fillet(0.8)
stator = cyl_z(0, FAN_Y, FZ0, FZ0 + 3.0, 5.5)
for k in range(3):
    ang = k * 120 + 90
    strut = box(9.5, 0, FZ0 + 1.0, 9.0, 1.2, 2.0).rotate((0, 0, 0), (0, 0, 1), ang).translate((0, FAN_Y, 0))
    stator = stator.union(strut)
add("Fan_Shroud", shroud, (0.95, 0.45, 0.05))
add("Fan_Stator", stator, DGREY)

rotor = cyl_z(0, FAN_Y, FZ0 + 3.2, FZ1 - 0.8, 5.8)
for k in range(9):
    bl = (box(9.5, 0, FZ0 + 5.2, 8.5, 0.9, 3.8)
          .rotate((9.5, 0, FZ0 + 5.2), (10.5, 0, FZ0 + 5.2), 32)
          .rotate((0, 0, 0), (0, 0, 1), k * 40)
          .translate((0, FAN_Y, 0)))
    rotor = rotor.union(bl)
add("Fan_Rotor", rotor, SILVER)

# ---------------- battery + canopy ----------------
BAT_CY = 16.0
bat = box(0, BAT_CY, PCB_TOP + 4.5, 18, 36, 9).edges().fillet(1.0)
add("Battery_2S_LiPo", bat, (0.95, 0.75, 0.10))

can_h = 12.0
can_o = box(0, BAT_CY, PCB_TOP + can_h / 2, 22, 42, can_h)
can_o = can_o.edges("|Z").fillet(6.0).faces(">Z").edges().fillet(2.5)
can_o = can_o.cut(box(0, BAT_CY, PCB_TOP + 5.2 - 0.01, 19.6, 37.6, 10.4))
# cooling vents
for i in range(5):
    can_o = can_o.cut(box(0, BAT_CY - 12 + i * 6, PCB_TOP + can_h - 0.5, 8, 1.6, 4))
try:
    txt = (cq.Workplane("XY").workplane(offset=PCB_TOP + can_h)
           .center(0, BAT_CY + 14).transformed(rotate=(0, 0, 90))
           .text("MM-01", 4.0, -0.4, combine=False, halign="center", valign="center"))
    can_o = can_o.cut(txt)
except Exception as e:
    print("text skipped:", e)
add("Canopy", can_o, RED)

# ---------------- sensors ----------------
def sensor(name, px, py, heading):
    z = PCB_TOP + 1.6
    for kind, lx, col in (("LED", -3.5, (0.45, 0.20, 0.75)), ("RX", 3.5, (0.12, 0.12, 0.14))):
        c = cq.Solid.makeCylinder(1.5, 3.0, V(lx, 0, z), V(0, 1, 0))
        d = cq.Solid.makeSphere(1.5, V(lx, 3.0, z), V(0, 1, 0), 0, 90, 360)
        base = box(lx, -0.5, PCB_TOP + 0.8, 3.0, 2.0, 1.6).val()
        sh = cq.Workplane("XY").add(c).union(cq.Workplane("XY").add(d)).union(cq.Workplane("XY").add(base))
        sh = sh.rotate((0, 0, 0), (0, 0, 1), heading).translate((px, py, 0))
        add(f"IR_{kind}_{name}", sh, col, 0.95 if kind == "LED" else 1.0)

sensor("FrontL", -9, 44.5, 8)
sensor("FrontR",  9, 44.5, -8)
sensor("DiagL", -26.5, 42, 52)
sensor("DiagR",  26.5, 42, -52)
sensor("SideL", -28.0, 28, 90)
sensor("SideR",  28.0, 28, -90)

# ---------------- electronics ----------------
def qfp(name, cx, cy, n, leadspan):
    body = box(cx, cy, PCB_TOP + 0.9, n, n, 1.4)
    leads = box(cx, cy, PCB_TOP + 0.35, leadspan, leadspan, 0.5).cut(box(cx, cy, PCB_TOP + 0.35, n, n, 0.7))
    add(name + "_Body", body, (0.04, 0.04, 0.05))
    add(name + "_Leads", leads, SILVER)

qfp("MCU_STM32", -19, 22, 7.0, 9.0)
add("IMU", box(19, 38, PCB_TOP + 0.45, 3, 3, 0.9), BLACK)
add("MotorDriver_L", box(-19, 8, PCB_TOP + 0.55, 5, 4.4, 1.1), BLACK)
add("MotorDriver_R", box(19, 8, PCB_TOP + 0.55, 5, 4.4, 1.1), BLACK)
add("Buck_Inductor", box(-19, 36, PCB_TOP + 1.0, 4.5, 4.5, 2.0), SILVER)
add("BT_Module", box(20, 22, PCB_TOP + 1.2, 13.2, 16.6, 2.4), (0.08, 0.15, 0.35))
add("BT_Shield", box(20, 20.5, PCB_TOP + 2.8, 11, 11, 0.8), SILVER)

usb = box(-27.8, -8, PCB_TOP + 1.7, 7.35, 9.0, 3.4).edges("|X").fillet(1.2)
add("USB_C", usb, SILVER)
add("Power_Switch", box(26.5, -8, PCB_TOP + 1.8, 8.5, 3.6, 3.6), SILVER)
add("Power_Switch_Knob", box(26.5, -8, PCB_TOP + 4.2, 3, 2.4, 1.2), RED)
for sx, tag in ((-1, "L"), (1, "R")):
    add(f"Button_{tag}", box(sx * 24, -26, PCB_TOP + 1.7, 6, 6, 3.4), SILVER)
    add(f"Button_Cap_{tag}", cyl_z(sx * 24, -26, PCB_TOP + 3.4, PCB_TOP + 5.0, 1.8), BLACK)
for i, x in enumerate((-6, -2, 2, 6)):
    add(f"Status_LED_{i}", box(x, 39, PCB_TOP + 0.4, 1.6, 0.8, 0.8), (0.1, 0.95, 0.95))

# board screws
for i, (x, y) in enumerate([(-26, -44), (26, -44), (-26, 44), (26, 44)]):
    pass  # kept out on purpose: sensors/skirt occupy these corners

# ---------------- assemble + export ----------------
assy = cq.Assembly(name="Micromouse_Velocity_MM01")
for n, shp, col in parts:
    assy.add(shp, name=n, color=col)
assy.save("/mnt/user-data/outputs/Micromouse_MM01.step", exportType="STEP")
print("parts:", len(parts))

if __name__ == "__main__":
    import pickle
    comp = cq.Compound.makeCompound([ (p[1].val() if hasattr(p[1], "val") else p[1]) for p in parts ])
    bb = comp.BoundingBox()
    print("BBox X %.1f  Y %.1f  Z %.1f" % (bb.xlen, bb.ylen, bb.zlen))
    print("min z %.2f" % bb.zmin)