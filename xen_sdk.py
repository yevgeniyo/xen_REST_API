import re
import sys
import xml.dom.minidom
import xmlrpclib

import XenAPI

from logger import logger

GB = 2 ** 30
MB = 2 ** 20


class XenSession:
    def __init__(self, url, username, password):
        self.url = url
        # First type of connection
        self.conn = xmlrpclib.Server(url)
        # Second type of connection
        self.session = XenAPI.Session(url)
        self.response = {"status": None, "data": [], "message": None}

        try:
            self.session.xenapi.login_with_password(username, password, "1.0", "")
            self.connection = self.conn.session.login_with_password(username, password)
            self.token = self.connection['Value']
        except XenAPI.Failure as f:
            logger.error("Failed to acquire a session: %s" % f.details)

    def __exit__(self, exc_type, exc_value, traceback):
        self.conn.xenapi.session.logout()

    # List of all VMs on the host
    # def list_of_vms_old(self):
    #     vms = self.session.xenapi.VM.get_all_records()
    #     vm = None
    #     for vm_ref in vms:
    #         vm_rec = vms[vm_ref]
    #         if not vm_rec['is_a_template'] and not vm_rec['is_control_domain']:
    #             self.response['status'] = 'success'
    #             self.response['data'].append(
    #                 {
    #                     'VM NAME': vm_rec['name_label'],
    #                     'POWER STATE': vm_rec['power_state'],
    #                     'CPU': vm_rec['VCPUs_max'],
    #                     'RAM': int(vm_rec['memory_static_max']) / GB,
    #                     'VM ID': vm_ref
    #                 }
    #             )
    #             vm = vm_ref
    #             # if vm is None:
    #             #     self.response['message'] = 'No VMs, host is empty'
    #     return self.response

    def list_of_vms(self):

        vms = self.conn.VM.get_all_records(self.token)['Value'].items()
        vif = self.conn.VIF.get_all_records(self.token)['Value'].items()
        vif = {i[0]: i[1] for i in vif}
        vm = None
        for tup in vms:
            vm_ref = tup[0]
            vm_rec = tup[1]
            if not vm_rec['is_a_template'] and not vm_rec['is_control_domain']:
                mac = []
                # print vm_rec['name_label'], len(vm_rec['VIFs'])
                for vif_opref in vm_rec['VIFs']:
                    mac.append(vif[vif_opref]['MAC'])
                    # print vif[vif_opref]['MAC']
                self.response['status'] = 'success'
                self.response['data'].append(
                    {
                        'VM NAME': vm_rec['name_label'],
                        'POWER STATE': vm_rec['power_state'],
                        'CPU': vm_rec['VCPUs_max'],
                        'RAM': int(vm_rec['memory_static_max']) / GB,
                        'VM ID': vm_ref,
                        'number of VIFs': len(vm_rec['VIFs']),
                        'MAC': mac,
                    }
                )

                vm = vm_ref
                # if vm is None:
                #     self.response['message'] = 'No VMs, host is empty'

        return self.response


# return True

    # Start VM on the host
    def start_vm(self, vmname):
        vms = self.session.xenapi.VM.get_all_records()
        vm = None
        for vm_ref in vms:
            vm_rec = vms[vm_ref]
            if vm_rec['name_label'] == vmname and not vm_rec['is_a_template'] and not vm_rec['is_control_domain'] \
                    and vm_rec["power_state"] == "Halted":
                vm = vm_ref
                break

        if vm is None:
            self.response['status'] = 'failed'
            self.response['message'] = "VM has already started or not exist"
            return self.response
            exit(1)

        task = self.session.xenapi.Async.VM.start(vm, False, True)
        task_record = self.session.xenapi.task.get_record(task)
        self.response["status"] = "success"
        self.response["message"] = "VM will start immediately"
        return self.response


    # Stop VM on the host
    def stop_vm(self, vmname):
        vms = self.session.xenapi.VM.get_all_records()
        vm = None
        for vm_ref in vms:
            vm_rec = vms[vm_ref]
            if vm_rec['name_label'] == vmname and not vm_rec['is_a_template'] and not vm_rec['is_control_domain'] \
                    and vm_rec["power_state"] == "Running":
                vm = vm_ref
                break

        if vm is None:
            self.response['status'] = 'failed'
            self.response['message'] = "VM has already stopped or not exist"
            return self.response
            exit(1)

        task = self.session.xenapi.Async.VM.hard_shutdown(vm)
        task_record = self.session.xenapi.task.get_record(task)
        self.response["status"] = "success"
        self.response["message"] = "VM will halt immediately"
        return self.response


    # Modify CPU on the host
    def mod_cpu(self, pool, vmname, new_cpu):
        VM = self.conn.VM

        vms = VM.get_all_records(self.token)
        vm = None
        OpaqueRefs = [i for i in vms['Value'] if i.startswith('OpaqueRef:')]
        for vm_ref in OpaqueRefs:
            vm_rec = vms['Value'][vm_ref]
            if vm_rec['name_label'] == vmname and not vm_rec['is_a_template'] and not vm_rec['is_control_domain']:
                if vm_rec["power_state"] == "Running":
                    self.response['status'] = "failed"
                    self.response['message'] = "VM is running, for modifying CPU switch off server"
                    return self.response
                    exit(1)
                vm = vm_ref

        VM.set_VCPUs_max(self.token, vm, str(new_cpu))
        VM.set_VCPUs_at_startup(self.token, vm, str(new_cpu))
        self.response['status'] = 'success'
        self.response['data'].append({
            'new CPU': int(new_cpu),
            'VM': vmname,
            'pool': pool,
            'HOST': self.url
        })
        return self.response


    # Modify RAM on the host
    def mod_ram(self, pool, vmname, new_ram):
        VM = self.conn.VM

        vms = VM.get_all_records(self.token)
        vm = None
        OpaqueRefs = [i for i in vms['Value'] if i.startswith('OpaqueRef:')]
        for vm_ref in OpaqueRefs:
            vm_rec = vms['Value'][vm_ref]
            if vm_rec['name_label'] == vmname and not vm_rec['is_a_template'] and not vm_rec['is_control_domain']:
                if vm_rec["power_state"] == "Running":
                    self.response['status'] = "failed"
                    self.response['message'] = "VM is running, for modifying RAM, switch off server"
                    return self.response
                    exit(1)
                vm = vm_ref

        mem_str = str(int(new_ram * GB))
        VM.set_memory_limits(self.token, vm, mem_str, mem_str, mem_str, mem_str)
        self.response['status'] = 'success'
        self.response['data'].append({
            'new RAM': int(new_ram),
            'VM': vmname,
            'pool': pool,
            'HOST': self.url
        })
        return self.response


class CreateVM:
    def __init__(self, url, username, password, poolname, vmname, number_of_nets, first_net, second_net, new_mem,
                 new_cpu, disk_size):
        self.url = url
        self.poolname = poolname
        self.vmname = vmname
        self.number_of_nets = number_of_nets
        self.new_mem = new_mem
        self.new_cpu = new_cpu
        self.disk_size = disk_size
        self.v = 'Value'
        self.conn = xmlrpclib.Server(self.url)
        disk_size = int(self.disk_size) * 1073741824
        self.disk_size = 'size="%s"' % disk_size
        first_net = re.sub('[a-z,A-Z]', '', first_net)
        second_net = re.sub('[a-z,A-Z]', '', second_net)
        self.first_net = int(first_net)
        self.second_net = int(second_net)
        self.response = {"status": None, "data": [], "message": None}

        try:
            self.connection = self.conn.session.login_with_password(username, password)
            self.token = self.connection['Value']
        except XenAPI.Failure as f:
            logger.error("Failed to acquire a session: %s" % f.details)

    def __exit__(self, exc_type, exc_value, traceback):
        self.conn.xenapi.session.logout()

    def set_vm(self, VM):
        """Set VM:
        - find requested template;
        - set VM name and description;
        - set kernel commands (non-interactive).
        """

        distro_name = re.compile("Debian Jessie 8.0")
        templates = [t[0] for t in VM.get_all_records(self.token)[self.v].items() if
                     re.search(distro_name, t[1]["name_label"])]
        if not templates:
            logger.error(" Template not found\n\n")
            sys.exit(4)
        template = templates[0]
        logger.info("Selected template: %s\n" % VM.get_name_label(self.token, template)[self.v])

        logger.info("Installing new VM from the template")
        self.new_vm = VM.clone(self.token, template, self.vmname)[self.v]

        logger.info("New VM name is %s\n" % self.vmname)
        VM.set_name_description(self.token, self.new_vm, "Created via API")

        # logger.info("Adding noninteractive to the kernel commandline\n")
        #    VM.set_PV_args(token, new_vm, "noninteractive")

        return self.new_vm

    def set_cpu(self, VM):
        """Set CPU:
        - set max number;
        - set start number.
        """

        VM.set_VCPUs_max(self.token, vm, str(self.new_cpu))
        VM.set_VCPUs_at_startup(self.token, vm, str(self.new_cpu))

    def set_mem(self, VM):
        """Set VM (static) memory"""

        mem_str = str(int(self.new_mem * GB))
        VM.set_memory_limits(self.token, vm, mem_str, mem_str, mem_str, mem_str)

    def get_pif(self, PIF, HOST, NET):
        """Find out PIF (Physical network interface) attached to the selected server"""

        pifs = PIF.get_all_records(self.token)
        pifs_host = HOST.get_PIFs(self.token, self.host_ref)[self.v]

        pifs_attached = [pifs[self.v][id] for id in pifs_host if pifs[self.v][id]['currently_attached']]
        lowest = min([p['device'] for p in pifs_attached])
        pif = [p for p in pifs_attached if p['device'] == lowest][0]

        self.network_ref = pif['network']
        logger.info("PIF is connected to: %s\n" % NET.get_name_label(self.token, self.network_ref)[self.v])

        return self.network_ref

    def get_pif_int(self, PIF, HOST, NET):
        """Find out PIF (Physical network interface) attached to the selected server"""

        pifs = PIF.get_all_records(self.token)
        pifs_host = HOST.get_PIFs(self.token, self.host_ref)[self.v]

        pifs_attached = [pifs[self.v][id] for id in pifs_host if pifs[self.v][id]['currently_attached']]
        highest = max([p['device'] for p in pifs_attached])
        pif = [p for p in pifs_attached if p['device'] == highest][0]

        self.network_ref_int = pif['network']
        logger.info("PIF is connected to: %s\n" % NET.get_name_label(self.token, self.network_ref_int)[self.v])

        return self.network_ref_int

    def set_network_one(self, VIF):
        """Set VIF (Virtual network interface) based on
        - vm;
        - network_ref. (PIF)
        """

        logger.info("Creating VIF\n")
        vif = {'device': '0',
               'network': self.network_ref,
               'VM': vm,
               'MAC': "",
               'MTU': "1500",
               "qos_algorithm_type": "",
               "qos_algorithm_params": {},
               "other_config": {}}

        VIF.create(self.token, vif)

    def set_network_two(self, VIF):
        logger.info("Creating VIF\n")
        vif_int = {'device': '1',
                   'network': self.network_ref_int,
                   'VM': vm,
                   'MAC': "",
                   'MTU': "1500",
                   "qos_algorithm_type": "",
                   "qos_algorithm_params": {},
                   "other_config": {}}

        VIF.create(self.token, vif_int)

    def get_local_disks(self, HOST, PBD, SR):
        """ Obtain info about all local disk attached to the selected server"""

        pbds = PBD.get_all_records(self.token)
        pbds_host = HOST.get_PBDs(self.token, self.host_ref)[self.v]

        # Choose  PBDs attached to the host where VM should be install
        sr_ref = [PBD.get_record(self.token, i)[self.v]['SR'] for i in pbds_host]
        sr = [SR.get_record(self.token, d)[self.v] for d in sr_ref]

        return [s for s in sr if s['type'] in ['ext', 'lvm'] and not s['shared']]

    def get_set_disk(self, disk, config, name):
        """Copy a setting from xml doc to another one"""

        temp = config.getAttribute(name)
        disk.setAttribute(name, temp)

    def parse_disk(self, element, doc):
        """ Copy disk settings from template to new VM
        (using get_set_disk function)"""

        vm_disk = doc.createElement("disk")
        self.get_set_disk(vm_disk, element, "device")
        self.get_set_disk(vm_disk, element, "size")
        self.get_set_disk(vm_disk, element, "sr")
        self.get_set_disk(vm_disk, element, "bootable")
        return vm_disk

    def set_disks(self, HOST, VM, PBD, SR, VBD, VDI):
        """ Prepare HDD for main OS """
        #    size = disk
        logger.info("Choosing an SR to initiate the VM's disks")
        # Find local disk - in future give a choice to find maybe share storage as well
        for sr in self.get_local_disks(HOST, PBD, SR):
            logger.info("Found a local disk called '%s'" % sr['name_label'])
            logger.info("Physical size: %s" % (sr['physical_size']))
            percentage = float(sr['physical_utilisation']) / (float(sr['physical_size'])) * 100
            logger.info("Utilization: %5.2f %%" % (percentage))
            local_sr = sr
        local_sr_uuid = local_sr['uuid']
        logger.info("Chosen SR: %s (uuid %s)" % (local_sr['name_label'], local_sr['uuid']))

        logger.info("Rewriting the disk provisioning XML\n")
        # Get disks settings store in template->other configs (XML)
        disks_config = VM.get_other_config(self.token, vm)[self.v]['disks']
        #    disks_config = re.sub('size="([0-9]*)"','size="16589934592"', disks_config)
        disks_config = re.sub('size="([0-9]*)"', self.disk_size, disks_config)
        # print disks_confg
        xml_template = xml.dom.minidom.parseString(disks_config)
        xml_provision_template = xml_template.getElementsByTagName("provision")
        if len(xml_provision_template) <> 1:
            raise "Expected to find exactly one <provision> element"
        xml_disks_template = xml_provision_template[0].getElementsByTagName("disk")
        # Prepare disks settings for new VM (XML)
        xml_newvm = xml.dom.minidom.Document()
        xml_provision_newvm = xml_newvm.createElement("provision")
        for disk in xml_disks_template:
            disk.setAttribute("sr", local_sr_uuid)  # set up new sr_uuid
            xml_provision_newvm.appendChild(self.parse_disk(disk, xml_newvm))
        xml_newvm.appendChild(xml_provision_newvm)
        new_disk_config = xml_newvm.toprettyxml()

        global disks_number
        disks_number = len(xml_disks_template)
        logger.info("Asking server to provision storage from the template specification")
        try:
            VM.remove_from_other_config(self.token, vm, "disks")
        except:
            pass
        VM.add_to_other_config(self.token, vm, "disks", new_disk_config)
        VM.provision(self.token, vm)

        logger.info("Setting up names for assign disks")
        names = {
            '0': 'Main disk for %s' % self.vmname,
        }
        for vbd_ref in VM.get_VBDs(self.token, vm)[self.v]:
            position = VBD.get_userdevice(self.token, vbd_ref)[self.v]
            vdi_ref = VBD.get_VDI(self.token, vbd_ref)[self.v]
            VDI.set_name_label(self.token, vdi_ref, names[position])

    ### MAIN START HERE ###
    def main(self):
        VM = self.conn.VM
        HOST = self.conn.host
        VDI = self.conn.VDI
        PIF = self.conn.PIF
        VIF = self.conn.VIF
        NET = self.conn.network
        PBD = self.conn.PBD
        SR = self.conn.SR
        VBD = self.conn.VBD
        VDI = self.conn.VDI
        self.token = self.connection[self.v]

        # These variables are 'read only' used in various functions
        # so I can define them global here and not bother to pass
        # to functions as argument later

        global host_ref  # Ref: Host to install
        self.host_ref = HOST.get_by_name_label(self.token, self.poolname)[self.v][0]

        global network_ref  # Ref: Network
        self.network_ref = self.get_pif(PIF, HOST, NET)

        global network_ref_int  # Ref: Network
        self.network_ref_int = self.get_pif_int(PIF, HOST, NET)

        global vm  # Ref: to the new VM
        vm = self.set_vm(VM)  # create VM

        self.set_cpu(VM)  # set CPU
        self.set_mem(VM)  # set memory (only static value)
        if self.number_of_nets == 1 and self.first_net == 0:
            self.set_network_one(VIF)
        elif self.number_of_nets == 1 and self.first_net == 1:
            self.set_network_two(VIF)
        else:
            self.set_network_one(VIF)
            self.set_network_two(VIF)
        self.set_disks(HOST, VM, PBD, SR, VBD, VDI)  # prepare HDD disks

        logger.info("Starting VM")
        VM.start(self.token, vm, False, True)
        logger.info("VM is booting")

        self.response['status'] = 'success'
        self.response['message'] = 'VM has been created successfully'
        self.response['data'].append(
            {
                'VM NAME': self.vmname,
                'CPU': self.new_cpu,
                'RAM': self.new_mem,
            }
        )
        return self.response


class XenStatistics:
    def __init__(self, url, poolname, username, password):
        self.username = username
        self.password = password
        self.url = url
        self.poolname = poolname
        self.conn = xmlrpclib.Server(url)
        self.response = {"status": None, "data": [], "message": None}
        self.v = 'Value'

        try:
            self.connection = self.conn.session.login_with_password(username, password)
            self.token = self.connection['Value']
        except XenAPI.Failure as f:
            logger.error("Failed to acquire a session: %s" % f.details)

    def __exit__(self, exc_type, exc_value, traceback):
        self.conn.xenapi.session.logout()
        # Get local storage statistics


    # Disk statistics

    def get_local_disks(self, HOST, PBD, SR):
        """ Obtain info about all local disk attached to the selected server"""
        pbds = PBD.get_all_records(self.token)
        pbds_host = HOST.get_PBDs(self.token, self.host_ref)[self.v]

        # Choose  PBDs attached to the host where VM should be install
        sr_ref = [PBD.get_record(self.token, i)[self.v]['SR'] for i in pbds_host]
        sr = [SR.get_record(self.token, d)[self.v] for d in sr_ref]

        return [s for s in sr if s['type'] in ['ext', 'lvm'] and not s['shared']]

    def get_storage_stat(self, HOST, PBD, SR):
        """ Get capacity of local storage """
        logger.info("Choosing an SR")
        # Find local disk - in future give a choice to find maybe share storage as well
        for sr in self.get_local_disks(HOST, PBD, SR):
            logger.info("Found a local disk called '%s'" % sr['name_label'])
            logger.info("Physical size: %s" % (sr['physical_size']))
            percentage = float(sr['physical_utilisation']) / (float(sr['physical_size'])) * 100
            logger.info("Utilization: %5.2f %%" % (percentage))
            self.response['status'] = 'success'
            self.response['message'] = 'Local storage capacity'
            self.response['data'].append(
                {
                    'HOST': self.url,
                    'PHYSICAL SIZE': sr['physical_size'],
                    'USED': sr['physical_utilisation'],
                    'PERCENTAGE OF UTILIZATION': "%5.2f %%" % (percentage),
                }
            )

    def storage(self):
        HOST = self.conn.host
        PBD = self.conn.PBD
        SR = self.conn.SR

        global host_ref  # Ref: Host to install
        self.host_ref = HOST.get_by_name_label(self.token, self.poolname)[self.v][0]

        self.get_storage_stat(HOST, PBD, SR)
        return self.response


    # RAM statistics

    def get_ram_stat(self):

        bytes = float(1073741824)
        all_ram = self.conn.host_metrics.get_all_records(self.token)['Value']
        all_ram = all_ram.values()[0]

        hosts_list = XenSession(self.url, self.username, self.password)
        hosts_list = hosts_list.list_of_vms()['data']
        vms_ram = 0
        for vm in hosts_list:
            vms_ram += int(vm['RAM'])


        self.response['status'] = 'success'
        self.response['message'] = 'Host memory usage (in bytes)'
        self.response['data'].append(
            {
                'HOST': self.url,
                'TOTAL MEMORY': round(float(all_ram['memory_total']), 0),
                'ACTUAL MEMORY USED': round((float(all_ram['memory_total']) - float(all_ram['memory_free'])), 0),
                'ACTUAL MEMORY FREE': round(float(all_ram['memory_free']), 0),
                'RESERVED MEMORY USED': float(vms_ram) * bytes,
                'RESERVED MEMORY FREE': round(float(all_ram['memory_total']), 0) - (vms_ram * bytes),
            }
        )
        return self.response
        #return all_ram


    # CPU statistics

    def get_cpu_stat(self):

        all_cpu = len(self.conn.host_cpu.get_all_records(self.token)['Value'])
        hosts_list = XenSession(self.url, self.username, self.password)
        hosts_list = hosts_list.list_of_vms()['data']
        vms_cpu = 0
        for vm in hosts_list:
            vms_cpu += int(vm['CPU'])

        self.response['status'] = 'success'
        self.response['message'] = 'Host CPU usage (if VMs CPU > TOTAL CPU, it means that not all VMs could run on this host simultaneously)'
        self.response['data'].append(
            {
                'HOST': self.url,
                'TOTAL CPU': all_cpu,
                'VMs CPU': vms_cpu,
            }
        )


        return self.response

