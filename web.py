#!flask/bin/python
from flask import Flask, jsonify, request
from flask_httpauth import HTTPBasicAuth

from xen_sdk import CreateVM
from xen_sdk import XenSession
from xen_sdk import XenStatistics

auth = HTTPBasicAuth()


app = Flask(__name__)
username = 'root'
password = '' # put here your xenservers password 



# Statusl VMs

@app.route('/api/v1', methods = ['GET'])
def help():
    """Print all available functions."""
    func_list = {}
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            func_list[rule.rule] = app.view_functions[rule.endpoint].__doc__
    return jsonify(func_list)

@app.route('/api/v1/pool/<poolname>/host/<hostip>/VM', methods = ['GET'])
#@auth.login_required
def list_of_running_vms(hostip, poolname):
    """list Vms."""
    url = 'http://{}'.format(str(hostip))
    xs = XenSession(url=url, username=username, password=password)
    return jsonify(xs.list_of_vms())


# Start one VM
@app.route('/api/v1/pool/<poolname>/host/<hostip>/VM/<vmname>/start', methods=['POST'])
#@auth.login_required
def start_one_vm(hostip,poolname, vmname):
    """start one vm """
    url = 'http://{}'.format(str(hostip))
    xs = XenSession(url=url, username=username, password=password)
    return jsonify(xs.start_vm(vmname=vmname))

# Stop on VM
@app.route('/api/v1/pool/<poolname>/host/<hostip>/VM/<vmname>/stop', methods=['POST'])
#@auth.login_required
def stop_one_vm(hostip, poolname, vmname):
    """stop one vm """
    url = 'http://{}'.format(str(hostip))
    xs = XenSession(url=url, username=username, password=password)
    return jsonify(xs.stop_vm(vmname=vmname))

# Modify CPU on existing VM
@app.route('/api/v1/pool/<poolname>/host/<hostip>/VM/<vmname>/CPU', methods=['POST'])
#@auth.login_required
def mod_cpu_api(hostip, poolname, vmname):
    """modify cpu """
    new_cpu = request.args.get('new_cpu')
    url = 'http://{}'.format(str(hostip))
    xs = XenSession(url=url, username=username, password=password)
    return jsonify(xs.mod_cpu(pool=poolname, vmname=vmname, new_cpu=int(new_cpu)))

# Modify RAM on existing VM
@app.route('/api/v1/pool/<poolname>/host/<hostip>/VM/<vmname>/RAM', methods=['POST'])
#@auth.login_required
def mod_ram_api(hostip, poolname, vmname):
    """modify ram """
    new_ram = request.args.get('new_ram')
    url = 'http://{}'.format(str(hostip))
    xs = XenSession(url=url, username=username, password=password)
    return jsonify(xs.mod_ram(pool=poolname, vmname=vmname, new_ram=int(new_ram)))

# Create new VM
@app.route('/api/v1/pool/<poolname>/host/<hostip>', methods=['POST'])
#@auth.login_required
def create_new_vm(hostip, poolname):
    """create ne VM """
    url = 'http://{}'.format(str(hostip))
    new_vmname = request.args.get('new_vmname')
    new_ram = int(request.args.get('new_ram'))
    new_cpu = int(request.args.get('new_cpu'))
    disk_size = int(request.args.get('disk_size'))
    number_nets = int(request.args.get('number_nets'))
    first_net = str(request.args.get('first_net'))
    second_net = str(request.args.get('second_net'))
    xy = CreateVM(url=url, username=username, password=password, poolname=poolname, vmname=new_vmname, \
                  number_of_nets=number_nets, first_net=first_net, second_net=second_net, new_mem=new_ram, \
                  new_cpu=new_cpu, disk_size=disk_size)
    return jsonify(xy.main())

# Storage stats
@app.route('/api/v1/pool/<poolname>/host/<hostip>', methods = ['GET'])
#@auth.login_required
def storage_usage(hostip, poolname):
    """storage statistics """
    url = 'http://{}'.format(str(hostip))
    report = request.args.get('report')
    if report == 'storage':
        xs = XenStatistics(url=url, poolname=poolname, username=username, password=password)
        return jsonify(xs.storage())
    elif report == 'ram':
        xs = XenStatistics(url=url, poolname=poolname, username=username, password=password)
        return jsonify(xs.get_ram_stat())
    elif report == 'cpu':
        xs = XenStatistics(url=url, poolname=poolname, username=username, password=password)
        return jsonify(xs.get_cpu_stat())
    else:
        return {}


if __name__ == '__main__':
    app.run()#debug=True, use_reloader=False)
