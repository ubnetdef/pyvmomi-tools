from os import path
import sys
sys.path.insert(0, path.abspath('./'))

from pyVim.connect import SmartConnect
from pyVmomi import vim, vmodl
import ssl
import pyvmomi_tools

username = "someone@vsphere.local"
password = "somepasswordhere"
host = "hostgoeshere"
template_name = "templatename"

si = SmartConnect(host=host, user=username, pwd=password)

# Create new VM
print("Creating new VM...")
template = pyvmomi_tools.get_vm_by_name(si, template_name)
newvm: vim.VirtualMachine = pyvmomi_tools.clone_vm(si, template, "pyvmomoi-testing", "UBNetDef", "blaketnr", None, None, "MAIN", True, None)
print(f"New VM with UUID '{newvm.config.uuid}' Created!")

# Retrieve MKS ticket
webmks = newvm.AcquireTicket("webmks")
print(f"WebMKS Ticket: {webmks.ticket}")
consoleURL = f"wss://arena.ubnetdef.org/console/{webmks.host}/{webmks.ticket}"
print(f"ConsoleURL: {consoleURL}")

# Delete VM
print("Deleting VM...")
pyvmomi_tools.force_delete_vm(newvm)
print("Deleted VM!")