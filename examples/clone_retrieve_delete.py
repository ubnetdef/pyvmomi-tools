from pyVim.connect import SmartConnect
from pyVmomi import vim, vmodl
import ssl
import pyvmomi_tools

username = "YOUR USERNAME HERE"
password = "YOUR PASSWORD HERE"
host = "YOUR HOST HERE"
template_name = "YOUR TEMPLATE NAME HERE"
newvm_name = "new-vm-name"
datacenter_name = "DATACENTER NAME HERE"
folder_to_create_under = "FOLDER HERE"
cluster_name = "CLUSTER NAME HERE"
datastorecluster_name = None

si = SmartConnect(host=host, user=username, pwd=password)

# Create new VM
print("Creating new VM...")
template = pyvmomi_tools.get_vm_by_name(si, template_name)
newvm: vim.VirtualMachine = pyvmomi_tools.clone_vm(si, template, newvm_name, datacenter_name, folder_to_create_under, None, None, "MAIN", False, datastorecluster_name)
print("New VM Created!")

# Retrieve VM
print("Retrieving VM by UUID...")
uuid = newvm.config.uuid
datacenter = pyvmomi_tools.get_obj_by_name(si, vim.Datacenter, datacenter_name)
test: vim.VirtualMachine = si.content.searchIndex.FindByUuid(datacenter, uuid, True)
ipaddress = pyvmomi_tools.wait_for_ip_address(test, 60)
print(f"Retrieved VM with ip {ipaddress}!")

# Delete VM
print("Deleting VM...")
task = test.Destroy()
pyvmomi_tools.wait_for_task(task)
print("Deleted VM!")