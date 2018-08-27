mkdir -p /opt/data/kolla
dd if=/dev/zero of=/opt/data/kolla/ceph-osd0.img bs=5M count=128
LOOP=$(losetup -f)
losetup $LOOP /opt/data/kolla/ceph-osd0.img
parted $LOOP -s -- mklabel gpt mkpart KOLLA_CEPH_OSD_BOOTSTRAP_BS_OSD1 1 -1

dd if=/dev/zero of=/opt/data/kolla/ceph-osd0-b.img bs=5M count=2048
LOOP=$(losetup -f)
losetup $LOOP /opt/data/kolla/ceph-osd0-b.img
parted $LOOP -s -- mklabel gpt mkpart KOLLA_CEPH_OSD_BOOTSTRAP_BS_OSD1_B 1 -1

dd if=/dev/zero of=/opt/data/kolla/ceph-osd0-w.img bs=5M count=256
LOOP=$(losetup -f)
losetup $LOOP /opt/data/kolla/ceph-osd0-w.img
parted $LOOP -s -- mklabel gpt mkpart KOLLA_CEPH_OSD_BOOTSTRAP_BS_OSD1_W 1 -1

dd if=/dev/zero of=/opt/data/kolla/ceph-osd0-d.img bs=5M count=256
LOOP=$(losetup -f)
losetup $LOOP /opt/data/kolla/ceph-osd0-d.img
parted $LOOP -s -- mklabel gpt mkpart KOLLA_CEPH_OSD_BOOTSTRAP_BS_OSD1_D 1 -1

partprobe

