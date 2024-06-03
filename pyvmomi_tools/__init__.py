from pyVim.connect import SmartConnect
from pyVmomi import vim, vmodl
import ssl
import pyVmomi
import time
from pyvmomi_tools import pchelper

# This was copied from vmware pyvmomi community samples
def collect_properties(si, view_ref, obj_type, path_set=None,
                       include_mors=False):
    """
    Collect properties for managed objects from a view ref

    Check the vSphere API documentation for example on retrieving
    object properties:

        - http://goo.gl/erbFDz

    Args:
        si          (ServiceInstance): ServiceInstance connection
        view_ref (pyVmomi.vim.view.*): Starting point of inventory navigation
        obj_type      (pyVmomi.vim.*): Type of managed object
        path_set               (list): List of properties to retrieve
        include_mors           (bool): If True include the managed objects
                                       refs in the result

    Returns:
        A list of properties for the managed objects

    """
    collector = si.content.propertyCollector

    # Create object specification to define the starting point of
    # inventory navigation
    obj_spec = pyVmomi.vmodl.query.PropertyCollector.ObjectSpec()
    obj_spec.obj = view_ref
    obj_spec.skip = True

    # Create a traversal specification to identify the path for collection
    traversal_spec = pyVmomi.vmodl.query.PropertyCollector.TraversalSpec()
    traversal_spec.name = 'traverseEntities'
    traversal_spec.path = 'view'
    traversal_spec.skip = False
    traversal_spec.type = view_ref.__class__
    obj_spec.selectSet = [traversal_spec]

    # Identify the properties to the retrieved
    property_spec = pyVmomi.vmodl.query.PropertyCollector.PropertySpec()
    property_spec.type = obj_type

    if not path_set:
        property_spec.all = True

    property_spec.pathSet = path_set

    # Add the object and property specification to the
    # property filter specification
    filter_spec = pyVmomi.vmodl.query.PropertyCollector.FilterSpec()
    filter_spec.objectSet = [obj_spec]
    filter_spec.propSet = [property_spec]

    # Retrieve properties
    props = collector.RetrieveContents([filter_spec])

    data = []
    for obj in props:
        properties = {}
        for prop in obj.propSet:
            properties[prop.name] = prop.val

        if include_mors:
            properties['obj'] = obj.obj

        data.append(properties)
    return data

def get_obj_by_name(si: vim.ServiceInstance, datatype: type, name: str):
    '''
    This uses the container view and property collector as it retrieves everything in 1 request, because normal iterating does not
    '''
    content = si.content
    root_folder = si.content.rootFolder
    view = si.content.viewManager.CreateContainerView(root_folder, [datatype], True)
    collector = si.content.propertyCollector
    properties = ['name']
    retrieved_objects = collect_properties(si, view, datatype, properties, True)

    for some_object in retrieved_objects:
        object_name = some_object['name']
        if(object_name == name):
            return some_object['obj']

def get_vm_by_name(si: vim.ServiceInstance, name: str) -> vim.VirtualMachine:
    '''
    This uses the container view and property collector as it retrieves all VMs in 1 request, while iterating does not
    '''
    root_folder = si.content.rootFolder
    view = si.content.viewManager.CreateContainerView(root_folder, [vim.VirtualMachine], True)
    collector = si.content.propertyCollector
    vm_properties = ['name']
    vm_data = collect_properties(si, view, vim.VirtualMachine, vm_properties, True)

    for vm in vm_data:
        vm_name = vm['name']
        if(vm_name == name):
            return vm['obj']
        
def all_vm_by_name(si: vim.ServiceInstance, name: str) -> list[vim.VirtualMachine]:
    '''
    This uses the container view and property collector as it retrieves all VMs in 1 request, while iterating does not
    '''
    root_folder = si.content.rootFolder
    view = si.content.viewManager.CreateContainerView(root_folder, [vim.VirtualMachine], True)
    collector = si.content.propertyCollector
    vm_properties = ['name']
    vm_data = collect_properties(si, view, vim.VirtualMachine, vm_properties, True)

    vms = []
    for vm in vm_data:
        vm_name = vm['name']
        if(vm_name == name):
            vms.append(vm)
            return vm['obj']
    return vms

# This was copied from vmware pyvmomi community samples
def wait_for_task(task):
    """ wait for a vCenter task to finish """
    task_done = False
    while not task_done:
        if task.info.state == 'success':
            return task.info.result

        if task.info.state == 'error':
            print("there was an error")
            print(task.info.error)
            task_done = True

# This was modified from vmware pyvmomi community samples
def search_for_resource_pool(content, vim_type, name, folder=None, recurse=True):
    """
    Search the managed object for the name and type specified

    Sample Usage:

    get_obj(content, [vim.Datastore], "Datastore Name")
    """
    if folder is None:
        folder = content.rootFolder

    obj = None
    container = content.viewManager.CreateContainerView(folder, vim_type, recurse)

    for managed_object_ref in container.view:
        if managed_object_ref.parent.name == name:
            obj = managed_object_ref
            break
    container.Destroy()
    return obj

# This was modified from vmware pyvmomi community samples
def clone_vm(
        si: vim.ServiceInstance, template: vim.VirtualMachine, vm_name: str, datacenter_name: str, vm_folder: str, datastore_name: str,
        cluster_name: str, resource_pool, power_on: bool, datastorecluster_name: str):
    """
    Clone a VM from a template/VM, datacenter_name, vm_folder, datastore_name
    cluster_name, resource_pool, and power_on are all optional.
    """
    # Some of the functions below were not updated to use faster get_obj_by_name because I didn't test them

    # if none git the first one
    datacenter = get_obj_by_name(si, vim.Datacenter, datacenter_name)

    content = si.content
    if vm_folder:
        destfolder = get_obj_by_name(si, vim.Folder, vm_folder)
    else:
        destfolder = datacenter.vmFolder

    if datastore_name:
        datastore = pchelper.search_for_obj(content, [vim.Datastore], datastore_name)
    else:
        datastore = pchelper.get_obj(
            content, [vim.Datastore], template.datastore[0].info.name)

    # if None, get the first one
    cluster = pchelper.search_for_obj(content, [vim.ClusterComputeResource], cluster_name)
    if not cluster:
        clusters = pchelper.get_all_obj(content, [vim.ResourcePool])
        cluster = list(clusters)[0]

    if resource_pool:
        resource_pool = search_for_resource_pool(content, [vim.ResourcePool], resource_pool)
    else:
        resource_pool = cluster.resourcePool

    vmconf = vim.vm.ConfigSpec()

    if datastorecluster_name:
        podsel = vim.storageDrs.PodSelectionSpec()
        pod = pchelper.get_obj(content, [vim.StoragePod], datastorecluster_name)
        podsel.storagePod = pod

        storagespec = vim.storageDrs.StoragePlacementSpec()
        storagespec.podSelectionSpec = podsel
        storagespec.type = 'create'
        storagespec.folder = destfolder
        storagespec.resourcePool = resource_pool
        storagespec.configSpec = vmconf

        try:
            rec = content.storageResourceManager.RecommendDatastores(
                storageSpec=storagespec)
            rec_action = rec.recommendations[0].action[0]
            real_datastore_name = rec_action.destination.name
        except Exception:
            real_datastore_name = template.datastore[0].info.name

        datastore = pchelper.get_obj(content, [vim.Datastore], real_datastore_name)

    # set relospec
    relospec = vim.vm.RelocateSpec()
    relospec.datastore = datastore
    relospec.pool = resource_pool

    clonespec = vim.vm.CloneSpec()
    clonespec.location = relospec
    clonespec.powerOn = power_on

    task = template.Clone(folder=destfolder, name=vm_name, spec=clonespec)
    return wait_for_task(task)

def wait_for_ip_address(vm: vim.VirtualMachine, timeout_seconds: int) -> str:
    '''
    This retrieves the first IP that shows in VCenter.
    Returns 'None' if no IP found

    Not tested with multiple IPs or IPv6.
    '''

    start_time = time.time()

    ip_address = None
    out_of_time = False
    while(ip_address == None and not out_of_time):
        ip_address = vm.summary.guest.ipAddress
        time.sleep(1)
        out_of_time = time.time() >= start_time + timeout_seconds

    return ip_address

def get_vm_by_ip(si: vim.ServiceInstance, ip_address: str):
    root_folder = si.content.rootFolder
    view = si.content.viewManager.CreateContainerView(root_folder, [vim.VirtualMachine], True)
    collector = si.content.propertyCollector
    properties_to_get = ["guest.ipAddress"]
    query_data = collect_properties(si, view, vim.VirtualMachine, properties_to_get, True)

    for query in query_data:
        vm_has_ip_address = 'guest.ipAddress' in query
        if(vm_has_ip_address and query['guest.ipAddress'] == ip_address):
            return query['obj']

def force_delete_vm(vm: vim.VirtualMachine):
    vm.Terminate()
    while(vm.runtime.powerState != "poweredOff"):
        time.sleep(1)
    vm.Destroy()