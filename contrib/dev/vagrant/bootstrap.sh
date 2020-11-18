#!/usr/bin/env bash
#
# Bootstrap script to configure all nodes.
#
# This script is intended to be used by vagrant to provision nodes.
# To use it, set it as 'PROVISION_SCRIPT' inside your Vagrantfile.custom.
# You can use Vagrantfile.custom.example as a template for this.

VM=$1
MODE=$2
KOLLA_PATH=$3
KOLLA_ANSIBLE_PATH=$4
KOLLA_CLI_PATH=$5
NUMBER_OF_COMPUTE_NODES=$6
NUMBER_OF_STORAGE_NODES=$7
NUMBER_OF_NETWORK_NODES=$8
NUMBER_OF_CONTROL_NODES=$9
NUMBER_OF_MONITOR_NODES=$10

export http_proxy=
export https_proxy=

if [ "$MODE" == 'aio' ]; then
    # Run registry on port 4000 since it may collide with keystone when doing AIO
    REGISTRY_PORT=4000
else
    REGISTRY_PORT=5000
fi
REGISTRY_URL="operator.local"
REGISTRY=${REGISTRY_URL}:${REGISTRY_PORT}
ADMIN_PROTOCOL="http"

function _ensure_lsb_release {
    if type lsb_release >/dev/null 2>&1; then
        return
    fi

    if type apt >/dev/null 2>&1; then
        apt -y install lsb-release
    elif type yum >/dev/null 2>&1; then
        yum -y install redhat-lsb-core
    fi
}

function _is_distro {
    if [[ -z "$DISTRO" ]]; then
        _ensure_lsb_release
        DISTRO=$(lsb_release -si)
    fi

    [[ "$DISTRO" == "$1" ]]
}

function is_ubuntu {
    _is_distro "Ubuntu"
}

function is_centos {
    _is_distro "CentOS"
}

# Install common packages and do some prepwork.
function prep_work {

    # This removes the fqdn from /etc/hosts's 127.0.0.1. This name.local will
    # resolve to the public IP instead of localhost.
    sed -i -r "s,^127\.0\.0\.1\s+.*,127\.0\.0\.1   localhost localhost.localdomain localhost4 localhost4.localdomain4," /etc/hosts

    if is_centos; then
        if [[ "$(systemctl is-enabled firewalld)" == "enabled" ]]; then
            systemctl stop firewalld
            systemctl disable firewalld
        fi
        yum -y install epel-release
        rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-EPEL-7
        yum -y install MySQL-python vim-enhanced python-pip python-devel gcc openssl-devel libffi-devel libxml2-devel libxslt-devel
    elif is_ubuntu; then
        if [[ "$(systemctl is-enabled ufw)" == "enabled" ]]; then
            systemctl stop ufw
            systemctl disable ufw
        fi
        apt update
        apt -y install python-mysqldb python-pip python-dev build-essential libssl-dev libffi-dev libxml2-dev libxslt-dev
    else
        echo "Unsupported Distro: $DISTRO" 1>&2
        exit 1
    fi

    pip install --upgrade docker
}

# Do some cleanup after the installation of kolla
function cleanup {
    if is_centos; then
        yum clean all
    elif is_ubuntu; then
        apt clean
    else
        echo "Unsupported Distro: $DISTRO" 1>&2
        exit 1
    fi
}

# Install and configure a quick&dirty docker daemon.
function install_docker {
    if is_centos; then
        cat >/etc/yum.repos.d/docker.repo <<-EOF
[dockerrepo]
name=Docker Repository
baseurl=https://yum.dockerproject.org/repo/main/centos/7
enabled=1
gpgcheck=1
gpgkey=https://yum.dockerproject.org/gpg
EOF
        # Also upgrade device-mapper here because of:
        # https://github.com/docker/docker/issues/12108
        # Upgrade lvm2 to get device-mapper installed
        yum -y install docker-engine lvm2 device-mapper

        # Despite it shipping with /etc/sysconfig/docker, Docker is not configured to
        # load it from it's service file.
        sed -i -r "s|(ExecStart)=(.+)|\1=/usr/bin/docker daemon --insecure-registry ${REGISTRY} --registry-mirror=http://${REGISTRY}|" /usr/lib/systemd/system/docker.service
        sed -i 's|^MountFlags=.*|MountFlags=shared|' /usr/lib/systemd/system/docker.service

        usermod -aG docker vagrant
    elif is_ubuntu; then
        apt-key adv --keyserver hkp://pgp.mit.edu:80 --recv-keys 58118E89F3A912897C070ADBF76221572C52609D
        echo "deb https://apt.dockerproject.org/repo ubuntu-xenial main" > /etc/apt/sources.list.d/docker.list
        apt update
        apt -y install docker-engine
        sed -i -r "s|(ExecStart)=(.+)|\1=/usr/bin/docker daemon --insecure-registry ${REGISTRY} --registry-mirror=http://${REGISTRY}|" /lib/systemd/system/docker.service
    else
        echo "Unsupported Distro: $DISTRO" 1>&2
        exit 1
    fi

    if [[ "${http_proxy}" != "" ]]; then
        mkdir -p /etc/systemd/system/docker.service.d
        cat >/etc/systemd/system/docker.service.d/http-proxy.conf <<-EOF
[Service]
Environment="HTTP_PROXY=${http_proxy}" "HTTPS_PROXY=${https_proxy}" "NO_PROXY=localhost,127.0.0.1,${REGISTRY_URL}"
EOF

        if [[ "$(grep http_ /etc/bashrc)" == "" ]]; then
            echo "export http_proxy=${http_proxy}" >> /etc/bashrc
            echo "export https_proxy=${https_proxy}" >> /etc/bashrc
        fi
    fi

    systemctl daemon-reload
    systemctl enable docker
    systemctl start docker
}

function configure_kolla {
    # Use local docker registry
    sed -i -r "s,^[# ]*namespace *=.+$,namespace = ${REGISTRY}/lokolla," /etc/kolla/kolla-build.conf
    sed -i -r "s,^[# ]*push *=.+$,push = True," /etc/kolla/kolla-build.conf
    kolla-cli property set docker_registry ${REGISTRY}
    kolla-cli property set docker_namespace lokolla
    kolla-cli property set docker_insecure_registry True
    # Set network interfaces
    kolla-cli property set network_interface eth1
    kolla-cli property set neutron_external_interface eth2
    # Set VIP address to be on the vagrant private network
    kolla-cli property set kolla_internal_vip_address 172.28.128.254
}

function configure_kolla_cli {
    # Run the CLI setup script
    pushd ${KOLLA_CLI_PATH}
    python ./cli_setup.py
    popd

    # Set up the kolla-cli inventory
    if [ "$MODE" == 'aio' ]; then
        kolla-cli setdeploy local
        kolla-cli host add localhost
        for group in control deployment compute monitoring network storage; do
            kolla-cli group addhost $group localhost
        done
    else
        for node_num in $(seq 1 ${NUMBER_OF_COMPUTE_NODES}); do
            node_name="compute0${node_num}"
            kolla-cli host add $node_name
            kolla-cli group addhost compute $node_name
        done

        for node_num in $(seq 1 ${NUMBER_OF_STORAGE_NODES}); do
            node_name="storage0${node_num}"
            kolla-cli host add $node_name
            kolla-cli group addhost storage $node_name
        done

        for node_num in $(seq 1 ${NUMBER_OF_NETWORK_NODES}); do
            node_name="network0${node_num}"
            kolla-cli host add $node_name
            kolla-cli group addhost network $node_name
        done

        for node_num in $(seq 1 ${NUMBER_OF_CONTROL_NODES}); do
            node_name="control0${node_num}"
            kolla-cli host add $node_name
            kolla-cli group addhost control $node_name
        done

        for node_num in $(seq 1 ${NUMBER_OF_MONITOR_NODES}); do
            node_name="monitor0${node_num}"
            kolla-cli host add $node_name
            kolla-cli group addhost monitoring $node_name
        done
    fi
}

# Configure the operator node and install some additional packages.
function configure_operator {
    if is_centos; then
        yum -y install git mariadb
    elif is_ubuntu; then
        apt -y install git mariadb-client selinux-utils
    else
        echo "Unsupported Distro: $DISTRO" 1>&2
        exit 1
    fi

    pip install --upgrade "ansible>=2" python-openstackclient python-neutronclient tox

    pip install ${KOLLA_ANSIBLE_PATH}
    pip install ${KOLLA_PATH}
    pip install ${KOLLA_CLI_PATH}

    # Set selinux to permissive
    if [[ "$(getenforce)" == "Enforcing" ]]; then
        sed -i -r "s,^SELINUX=.+$,SELINUX=permissive," /etc/selinux/config
        setenforce permissive
    fi

    tox -c ${KOLLA_PATH}/tox.ini -e genconfig
    mkdir -p /etc/kolla
    cp -r ${KOLLA_ANSIBLE_PATH}/etc/kolla/* /etc/kolla
    cp -r ${KOLLA_PATH}/etc/kolla/* /etc/kolla
    ${KOLLA_ANSIBLE_PATH}/tools/generate_passwords.py
    mkdir -p /usr/share/kolla
    chown -R vagrant: /etc/kolla /usr/share/kolla

    configure_kolla_cli
    configure_kolla

    # Make sure Ansible uses scp.
    cat > ~vagrant/.ansible.cfg <<EOF
[defaults]
forks=100
remote_user = root

[ssh_connection]
scp_if_ssh=True
EOF
    chown vagrant: ~vagrant/.ansible.cfg

    mkdir -p /etc/kolla/config/nova/
    cat > /etc/kolla/config/nova/nova-compute.conf <<EOF
[libvirt]
virt_type = qemu
cpu_mode = none
EOF

    # Launch a local registry (and mirror) to speed up pulling images.
    if [[ ! $(docker ps -a -q -f name=registry) ]]; then
        docker run -d \
            --name registry \
            --restart=always \
            -p ${REGISTRY_PORT}:5000 \
            -e STANDALONE=True \
            -e MIRROR_SOURCE=https://registry-1.docker.io \
            -e MIRROR_SOURCE_INDEX=https://index.docker.io \
            -e STORAGE_PATH=/var/lib/registry \
            -v /data/host/registry-storage:/var/lib/registry \
            registry:2
    fi
}

prep_work
install_docker

if [[ "$VM" == "operator" ]]; then
    configure_operator
fi

cleanup
