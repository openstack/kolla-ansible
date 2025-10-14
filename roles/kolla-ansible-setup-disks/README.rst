Prepare disks for Kolla-Ansible CI run.

**Role Variables**

.. zuul:rolevar:: kolla_ansible_setup_disks_filepath

   Path to allocated file passed to loopmount

.. zuul:rolevar:: kolla_ansible_setup_disks_lv_name

   Logical volume name to create (skipped if not set)

.. zuul:rolevar:: kolla_ansible_setup_disks_vg_name

   Volume group name to create
