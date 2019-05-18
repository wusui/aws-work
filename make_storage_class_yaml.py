""" Generate a storageclass yaml file """
import yaml
from collections import OrderedDict
from ocs import api_client as ac
from ocs.pod import Pod


def represent_dictionary_order(self, dict_data):
    """
    OrderedDict representer that preserves order in dictionaries.
    
    Probably will be replace when I find out the standard way yaml
    files get created in openshift.
    """
    return self.represent_mapping('tag:yaml.org,2002:map', dict_data.items())


yaml.add_representer(OrderedDict, represent_dictionary_order)


def get_ip_addrs(pod_type, namespace='openshift-storage'):
    """
    Get the ip address for all pods of a given type.

    Args:
        pod_type (string): pod type (mon, mgr, osd...)
        namespace (string): namespace in -n field of oc commands

    Returns:
        List of ip_addresses for all pods of the type specified
    """
    ret_list = []
    look_for = f"rook-ceph-{pod_type}"
    client = ac.get_api_client("OCRESTClient")
    for mon_pod in client.get_pods(namespace=namespace):
        if mon_pod.startswith(look_for):
            pd = Pod(mon_pod,namespace=namespace)
            ip_addr = pd.exec_command(cmd=['hostname','-i'])[0].strip()
            ret_list.append(ip_addr)
    return ret_list


def make_storageclass_yaml(metadata_name, ceph_type):
    """
    Generate a yaml file to be used to create storage classes.

    Args:
        metadata_name (string): name in metadata field
        ceph_type (string): ceph pod type (mon, osd, mgr...)

    Returns:
        yaml data that can be used to create a storage class
    """
    yaml_info = OrderedDict()
    yaml_info['apiVersion'] = 'storage.k8s.io/v1beta1'
    yaml_info['kind'] = 'StorageClass'
    yaml_info['metadata'] = {'name': metadata_name}
    yaml_info['provisioner'] = 'kubernetes.io/rbd'
    yaml_info['parameters'] = OrderedDict()
    addresses = get_ip_addrs(ceph_type)
    # This could be made into a lambda expression
    out_with_port = []
    for entry in addresses:
        out_with_port.append(f"{entry}:6789")
    yaml_info['parameters']['monitors'] = out_with_port
    yaml_info['parameters']['adminId'] = 'kube'
    yaml_info['parameters']['adminSecretName'] = 'ceph-secret'
    yaml_info['parameters']['adminSecretNamespace'] = 'kube-system'
    yaml_info['parameters']['pool'] = 'kube'
    yaml_info['parameters']['userId'] = 'kube'
    yaml_info['parameters']['userSecretName'] = 'ceph-secret-user'
    return yaml.dump(yaml_info)


if __name__ == "__main__":
    output = make_storageclass_yaml('aardvark', 'mon')
    print(output)
