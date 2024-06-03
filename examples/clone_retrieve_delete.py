from pyVim.connect import SmartConnect
from pyVmomi import vim, vmodl
import ssl
import pyvmomi_tools

username = "YOUR USERNAME HERE"
password = "YOUR PASSWORD HERE"
host = "YOUR HOST HERE"
template_name = "YOUR TEMPLATE NAME HERE"

si = SmartConnect(host=host, user=username, pwd=password)

# Create new VM
print("Creating new VM...")
template = pyvmomi_tools.get_vm_by_name(si, template_name)
newvm: vim.VirtualMachine = pyvmomi_tools.clone_vm(si, template, "kali-test", "UBNetDef", "blaketnr", None, None, "MAIN", False, None)
print("New VM Created!")

# Retrieve VM
print("Retrieving VM by UUID...")
uuid = newvm.config.uuid
datacenter = pyvmomi_tools.get_obj_by_name(si, vim.Datacenter, "UBNetDef")
test: vim.VirtualMachine = si.content.searchIndex.FindByUuid(datacenter, uuid, True)
print("Retrieved VM!")

# Delete VM
print("Deleting VM...")
task = test.Destroy()
pyvmomi_tools.wait_for_task(task)
print("Deleted VM!")