mkdir -p /opt/data/kolla
dd if=/dev/zero of=/opt/data/kolla/ceph-osd0.img bs=5M count=3072
LOOP=$(losetup -f)
losetup $LOOP /opt/data/kolla/ceph-osd0.img
parted $LOOP -s -- mklabel gpt mkpart KOLLA_CEPH_OSD_BOOTSTRAP_OSD1 0 14GB

dd if=/dev/zero of=/opt/data/kolla/ceph-journal0.img bs=5M count=1024
LOOP=$(losetup -f)
losetup $LOOP /opt/data/kolla/ceph-journal0.img
parted $LOOP -s -- mklabel gpt mkpart KOLLA_CEPH_OSD_BOOTSTRAP_OSD1_J 0 5GB

partprobe $LOOP

