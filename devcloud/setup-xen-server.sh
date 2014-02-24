#!/bin/bash

printUsage() {
	echo "Usage: $0 [options]"
	echo "	options:"
	echo "		-h|--help			prints this usage message"
	echo "		--extend-primary-storage DISK	extends the available size in primary storage"
	echo "						by attaching DISK to the SR"
	echo "		--mysql				installs and configures mysql-server"
	echo "		--secondary-storage-nfs  PATH	configures NFS export for secondary storage under PATH"		
}

extendPrimaryPartition() {
	echo "Add $PRIMARY_STORAGE_DISK to primary storage SR"
	$PRIMARY_STORAGE_DISK=$1

	fdisk $PRIMARY_STORAGE_DISK > /dev/null << EOF
n
p
1


t
8e
w
EOF
	PRIMARY_STORAGE_PARTITION=${PRIMARY_STORAGE_DISK}1
	pvcreate $PRIMARY_STORAGE_PARTITION
	VG_NAME=$(vgdisplay -c | cut -d : -f 1)
	vgextend $VG_NAME $PRIMARY_STORAGE_PARTITION
}

doMySQL() {
	if [ -z "$(which mysqld_safe)" ]; then
		echo "Installing MySQL Server"
		yum -q -y --enablerepo="*" install mysql-server
	fi
	echo "Starting MySQL Server"
	/etc/init.d/mysqld restart
	echo "Setting up root access to MySQL server"
	/usr/bin/mysqladmin -u root -h localhost password "$ROOT_PASSWORD"
	mysql -h localhost -u root --password=$ROOT_PASSWORD -e "GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' IDENTIFIED BY \"$ROOT_PASSWORD\" WITH GRANT OPTION; FLUSH PRIVILEGES"
	echo "Configuring MySQL server to start at boot"
	chkconfig --add mysqld
	chkconfig mysqld on
}

doSecondaryStorageNFS() {
	SECONDARY_STORAGE_NFS_DISK=$1
	SECONDARY_STORAGE_DIR=$2

	SECONDARY_STORAGE_NFS_PARTITION=${SECONDARY_STORAGE_NFS_DISK}1
	echo "Creating filesystem on $SECONDARY_STORAGE_NFS_DISK"
	fdisk $SECONDARY_STORAGE_NFS_DISK > /dev/null << EOF
n
p
1


w
EOF
	sleep 5
	mkfs.ext3 -j -L "secondary storage" $SECONDARY_STORAGE_NFS_PARTITION > /dev/null
	echo "Creating secondary storage directory at $SECONDARY_STORAGE_DIR"
	mkdir -p $SECONDARY_STORAGE_DIR
	echo "Mounting $SECONDARY_STORAGE_NFS_PARTITION on $SECONDARY_STORAGE_DIR" 
	mount $SECONDARY_STORAGE_NFS_PARTITION $SECONDARY_STORAGE_DIR
	echo "$SECONDARY_STORAGE_DIR *(rw,async,no_subtree_check)" > /etc/exports
	exportfs -r 
	echo "Configuring and restarting portmap"
	echo "PMAP_ARGS=\"\"" > /etc/sysconfig/portmap
	/etc/init.d/portmap restart
	echo "Restarting NFS"
	/etc/init.d/nfs restart
	/etc/init.d/nfslock restart
}


ROOT_PASSWORD=changeme
SECONDARY_STORAGE_DIR=/opt/storage/secondary
BAD_PRIMARY_STORAGE_DISK=1
NO_PRIMARY_STORAGE_DISK=2
BAD_SECONDARY_STORAGE_DISK=3
NO_SECONDARY_STORAGE_DISK=4

# read options
while test $# -gt 0; do
        case "$1" in
		-h|--help)
			printUsage
			exit
			;;
                --extend-primary-storage)
                        shift
                        if test $# -gt 0; then
                                PRIMARY_STORAGE_DISK=$1
				if [ ! -b $PRIMARY_STORAGE_DISK ]; then
					echo "The specified primary storage disk $PRIMARY_STORAGE_DISK does not exists."
					exit $BAD_PRIMARY_STORAGE_DISK
				fi
                        else
                                echo "No disk for primary storage specified"
                                exit $NO_PRIMARY_STORAGE_DISK
                        fi
                        shift
                        ;;
                --mysql)
                        DO_MYSQL=1
                        shift
                        ;;
                --secondary-storage-nfs)
                        shift
                        if test $# -gt 0; then
                        	SECONDARY_STORAGE_NFS_DISK=$1
				if [ ! -b $SECONDARY_STORAGE_NFS_DISK ]; then
					echo "The specified secondary storage disk $SECONDARY_STORAGE_NFS_DISK does not exists."
					exit $BAD_SECONDARY_STORAGE_DISK
				fi

                        else
                                echo "No disk for secondary storage specified"
                                exit $NO_SECONDARY_STORAGE_DISK
                        fi
                        shift
                        ;;
                *)
                        break
                        ;;
        esac
done


YUM_MEDIA_REPO=/etc/yum.repos.d/CentOS-Media.repo
if [ -e $YUM_MEDIA_REPO ]; then
	echo "Found CentOS media repo but CD is most likely not avaliable, thus will remove repo" 
	rm -f $YUM_MEDIA_REPO
fi

if [ ! -e $(which vim) ]; then
	echo "VIM not found, intalling it now"
	yum -y -q --enablerepo="*" install vim-enhanced
fi

[ -n "$(xe template-list)" ] || echo "Creating VM templates"; /opt/xensource/libexec/create_templates

echo "Clearing iptables"
iptables -F
iptables -F -t nat
iptables --delete-chain RH-Firewall-1-INPUT
iptables-save > /dev/null

echo "Create SR for primary storage"
XE_HOST=$(xe host-list  | grep "uuid ( RO)" | sed -e "s/uuid ( RO)[ \t]*: //")
xe sr-create type=lvm content-type=user name-label="primary storage" device-config:device=/dev/sda3 host-uuid=$XE_HOST

CLOUD_BIN_DIR=/opt/cloud/bin
if [ ! -d $CLOUD_BIN_DIR ]; then
	echo "Cloud tools directory does not exist yet and needs to be created"
	mkdir -p /opt/cloud/bin
fi
cd $CLOUD_BIN_DIR
VHD_UTIL_TOOL=$(which vhd-util)
if [ ! -e $VHD_UTIL_TOOL ]; then
	echo "VHD-Util tool is not present and needs to be downloaded"
	wget http://download.cloud.com.s3.amazonaws.com/tools/vhd-util
	chmod +x vhd-util
else
	echo "VHD-Util tool is present at $VHD_UTIL_TOOL and, if necessary, a link will be created at $CLOUD_BIN_DIR"
	if [ ! -e ${CLOUD_BIN_DIR}/vhd-util ]; then
		ln -s $VHD_UTIL_TOOL
	fi
fi
cd - > /dev/null

if [ "$PRIMARY_STORAGE_DISK" != "" ]; then
	extendPrimaryPartition $PRIMARY_STORAGE_DISK
fi

if [ "$DO_MYSQL" != "" ]; then
	doMySQL
fi

if [ "$SECONDARY_STORAGE_NFS_DISK" != "" ]; then
	doSecondaryStorageNFS $SECONDARY_STORAGE_NFS_DISK $SECONDARY_STORAGE_DIR

	echo "NFS configured to serve $SECONDARY_STORAGE_DIR as mount point,"
	echo "however you still need to provide the contents"
fi
