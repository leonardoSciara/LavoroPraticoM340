from flask import Blueprint
import requests
import urllib3
import os
import time
from dotenv import load_dotenv

load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Blueprint('api', __name__)

PROXMOX_HOSTS = ['192.168.56.15', '192.168.56.16', '192.168.56.17']
PROXMOX_PORT = 8006
PROXMOX_TOKEN_ID = os.getenv('PX_TOKEN_ID')
PROXMOX_TOKEN_SECRET = os.getenv('PX_TOKEN_SECRET')
PROXMOX_NODES = ['px1', 'px2', 'px3']
PROXMOX_STORAGE = 'local-lvm'
PROXMOX_TEMPLATE_IDS = [101, 102, 103]
CT_TYPE_TO_NODE = {'Gold': 0, 'Silver': 1, 'Bronze': 2}

def get_proxmox_url(host):
    return f'https://{host}:{PROXMOX_PORT}/api2/json'

def get_auth_headers():
    return {'Authorization': f'PVEAPIToken={PROXMOX_TOKEN_ID}={PROXMOX_TOKEN_SECRET}'}

def get_next_ctid():
    host = PROXMOX_HOSTS[0]
    url = f'{get_proxmox_url(host)}/cluster/nextid'
    try:
        r = requests.get(url, headers=get_auth_headers(), verify=False)
        if r.status_code != 200:
            return None
        return int(r.json()['data'])
    except Exception:
        return None


def start_container(node_index, ctid):
    host = PROXMOX_HOSTS[node_index]
    node = PROXMOX_NODES[node_index]
    url = f'{get_proxmox_url(host)}/nodes/{node}/lxc/{ctid}/status/start'
    try:
        r = requests.post(url, headers=get_auth_headers(), verify=False)
        if r.status_code != 200:
            try:
                error_data = r.json()
                error_msg = error_data.get('message', r.text)
            except:
                error_msg = r.text
            return False
        return True
    except Exception:
        return False

#ChatGPT Mi ha aiutato per scrivere questa funzione
def get_container_ip(host, node, ctid, timeout=120):
    import re, time, os, requests

    PROXMOX_DEBUG = os.getenv('PROXMOX_DEBUG')
    url = f'{get_proxmox_url(host)}/nodes/{node}/lxc/{ctid}/interfaces'

    def is_private_ip(ip):
        if ip.startswith('10.') or ip.startswith('192.168.'):
            return True
        return bool(re.match(r'^172\.(1[6-9]|2[0-9]|3[0-1])\.', ip))

    def is_loopback_or_linklocal(ip):
        return ip.startswith('127.') or ip.startswith('169.254.')

    def extract_ipv4(addresses):
        if not addresses:
            return None
        candidates = []
        if isinstance(addresses, list):
            for addr in addresses:
                ip = addr.get('ip-address') or addr.get('address') or addr.get('ip') or addr.get('ipv4') if isinstance(addr, dict) else addr
                if ip:
                    m = re.search(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", str(ip))
                    if m: candidates.append(m.group(0))
        elif isinstance(addresses, str):
            m = re.search(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", addresses)
            if m: candidates.append(m.group(0))
        for ip in candidates:
            if not is_loopback_or_linklocal(ip) and is_private_ip(ip): return ip
        for ip in candidates:
            if not is_loopback_or_linklocal(ip): return ip
        return candidates[0] if candidates else None

    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, headers=get_auth_headers(), verify=False)
            if r.status_code != 200:
                time.sleep(3)
                continue
            data = r.json().get('data', {})
        except Exception:
            time.sleep(3)
            continue

        if isinstance(data, dict):
            loopback_ip = None
            for key in ('eth0', 'net0'):
                iface = data.get(key)
                if iface:
                    addresses = iface.get('addresses') if isinstance(iface, dict) else iface
                    ip = extract_ipv4(addresses)
                    if ip and not is_loopback_or_linklocal(ip):
                        return ip
                    elif ip:
                        loopback_ip = ip
            fallback_ip = None
            for iface in data.values():
                addresses = iface.get('addresses') if isinstance(iface, dict) else iface
                ip = extract_ipv4(addresses)
                if ip and not is_loopback_or_linklocal(ip): return ip
                if ip and not fallback_ip: fallback_ip = ip
            if loopback_ip and not fallback_ip: return loopback_ip
            if fallback_ip: return fallback_ip

        elif isinstance(data, list):
            candidates = []
            for iface in data:
                if isinstance(iface, dict):
                    addresses = iface.get('addresses') or iface.get('ip-addresses') or iface.get('ips') or iface.get('ip') or iface.get('ipv4')
                    ip = extract_ipv4(addresses)
                    if ip and not is_loopback_or_linklocal(ip):
                        if is_private_ip(ip): return ip
                        candidates.append(ip)
                    ip = iface.get('ip') or iface.get('address') or iface.get('ip-address')
                    if ip and re.search(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", str(ip)):
                        ip = str(ip).split('/')[0]
                        if not is_loopback_or_linklocal(ip):
                            if is_private_ip(ip): return ip
                            candidates.append(ip)
                elif isinstance(iface, str):
                    ip = extract_ipv4(iface)
                    if ip and not is_loopback_or_linklocal(ip): return ip
            if candidates: return candidates[0]

        if PROXMOX_DEBUG:
            try: print(f"[PROXMOX DEBUG] URL: {url} RESPONSE: {r.json()}")
            except Exception: print(f"[PROXMOX DEBUG] URL: {url} RESPONSE TEXT: {r.text}")

        time.sleep(3)

    return None


def clone_container(node_index, new_ctid, ct_type, ip=None):
    host = PROXMOX_HOSTS[node_index]
    node = PROXMOX_NODES[node_index]
    template_id = PROXMOX_TEMPLATE_IDS[node_index]
    
    params = {
        'newid': new_ctid,
        'hostname': f'ct-{ct_type.lower()}-{new_ctid}',
        'storage': PROXMOX_STORAGE,
        'full': 1,
    }
    
    try:
        url = f'{get_proxmox_url(host)}/nodes/{node}/lxc/{template_id}/clone'
        r = requests.post(url, headers=get_auth_headers(), data=params, verify=False)
        if r.status_code != 200:
            try:
                error_data = r.json()
                error_msg = error_data.get('message', r.text)
                if error_data.get('data'):
                    error_msg += f" (Dati: {error_data.get('data')})"
            except:
                error_msg = r.text
            return {'success': False, 'error': error_msg}
        
        upid = r.json()['data']
        
        timeout = 300
        start_time = time.time()
        while True:
            url_task = f'{get_proxmox_url(host)}/nodes/{node}/tasks/{upid}/status'
            r_task = requests.get(url_task, headers=get_auth_headers(), verify=False)
            task_data = r_task.json().get('data', {})
            
            if task_data.get('status') == 'stopped':
                if task_data.get('exitstatus') == 'OK':
                    break
                return {'success': False, 'error': f"Clone fallito, exitstatus={task_data.get('exitstatus')}"}
            
            if time.time() - start_time > timeout:
                return {'success': False, 'error': 'Timeout clone'}
            
            time.sleep(2)
        
        if not start_container(node_index, new_ctid):
            return {'success': False, 'error': 'Avvio container fallito'}
        
        ip_real = get_container_ip(host, node, new_ctid) or ip
        
        return {
            'success': True,
            'ct_vmid': new_ctid,
            'ip': ip_real,
            'ct_user': 'root',
            'ct_password': 'Password&1'
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

def create_ct(ct_type, node_index=None, ip=None):
    if node_index is None:
        node_index = CT_TYPE_TO_NODE.get(ct_type)
        if node_index is None:
            return {'success': False, 'error': f'Tipo CT {ct_type} non valido'}

    ctid = get_next_ctid()
    if ctid is None:
        return {'success': False, 'error': 'Impossibile ottenere CTID'}

    return clone_container(node_index, ctid, ct_type, ip=ip) 
