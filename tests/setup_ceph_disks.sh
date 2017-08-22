mkdir -p /opt/data/kolla
dd if=/dev/zero of=/opt/data/kolla/ceph-osd0.img bs=5M count=2048
LOOP=$(losetup -f)
losetup $LOOP /opt/data/kolla/ceph-osd0.img
parted $LOOP -s -- mklabel gpt mkpart KOLLA_CEPH_OSD_BOOTSTRAP_OSD1 1 -1

dd if=/dev/zero of=/opt/data/kolla/ceph-journal0.img bs=5M count=512
LOOP=$(losetup -f)
losetup $LOOP /opt/data/kolla/ceph-journal0.img
parted $LOOP -s -- mklabel gpt mkpart KOLLA_CEPH_OSD_BOOTSTRAP_OSD1_J 1 -1

partprobe $LOOP

