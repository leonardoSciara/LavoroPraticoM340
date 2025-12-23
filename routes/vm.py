from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from models.model import user_has_role, CTRequest, User
from models.connection import db
from routes.api import create_ct, get_container_ip, PROXMOX_HOSTS, PROXMOX_NODES, CT_TYPE_TO_NODE

from datetime import datetime

app = Blueprint('ct', __name__)

MACHINE_TYPES = [
    {'id': 'bronze', 'name': 'Bronze', 'cpu': 1, 'ram': 2, 'desc': 'Base CT'},
    {'id': 'silver', 'name': 'Silver', 'cpu': 2, 'ram': 4, 'desc': 'Med CT'},
    {'id': 'gold', 'name': 'Gold', 'cpu': 4, 'ram': 8, 'desc': 'High CT'}
]

@app.route('/dashboard')
@login_required
def ct_dashboard():
    if current_user.has_role('admin'):
        return redirect(url_for('ct.admin_ct_dashboard'))

    ct_requests = CTRequest.query.filter_by(user_id=current_user.id)\
        .order_by(CTRequest.created_at.desc()).all()
    return render_template('dashboard.html', 
                         machine_types=MACHINE_TYPES, 
                         requests=ct_requests)

@app.route('/request_ct', methods=['POST'])
@login_required
def request_ct():
    machine_id = request.form.get('machine_type')
    machine = next((m for m in MACHINE_TYPES if m['id'] == machine_id), None)
    
    if not machine:
        flash('Tipo macchina non valido')
        return redirect(url_for('ct.ct_dashboard'))
    
    ct_request = CTRequest(
        user_id=current_user.id,
        machine_type=machine['id'],
        machine_name=machine['name'],
        machine_cpu=machine['cpu'],
        machine_ram=machine['ram'],
        status='pending'
    )
    
    db.session.add(ct_request)
    db.session.commit()
    
    flash('Richiesta inviata, in attesa di approvazione')
    return redirect(url_for('ct.ct_dashboard'))

@app.route('/admin/dashboard')
@login_required
@user_has_role('admin')
def admin_ct_dashboard():
    requests = CTRequest.query.order_by(CTRequest.created_at.desc()).all()
    return render_template('admin_dashboard.html', requests=requests) 

@app.route('/admin/validate/<int:req_id>', methods=['POST'])
@login_required
@user_has_role('admin')
def validate_ct(req_id):
    req = CTRequest.query.get_or_404(req_id)

    if req.status != 'pending':
        flash('Richiesta già processata')
        return redirect(url_for('ct.admin_ct_dashboard'))
    
    ct_type = req.machine_name
    result = create_ct(ct_type)
    
    if result.get('success'):
        req.status = 'approved'
        req.ct_ip = result['ip']
        req.ct_hostname = f'ct-{ct_type.lower()}-{result["ct_vmid"]}'
        req.ct_user = result['ct_user']
        req.ct_password = result['ct_password']
        req.ct_vmid = result['ct_vmid']
        
        db.session.commit()
        flash('CT creata e approvata con successo')
    else:
        flash(f'Errore nella creazione del CT: {result.get("error", "Errore sconosciuto")}')
    
    return redirect(url_for('ct.admin_ct_dashboard'))


@app.route('/admin/reject/<int:req_id>', methods=['POST'])
@login_required
@user_has_role('admin')
def reject_ct(req_id):
    req = CTRequest.query.get_or_404(req_id)
    if req.status != 'pending':
        flash('Richiesta già processata')
        return redirect(url_for('ct.admin_ct_dashboard'))

    req.status = 'rejected'
    db.session.commit()
    flash('Richiesta rifiutata')
    return redirect(url_for('ct.admin_ct_dashboard'))


@app.route('/request/delete/<int:req_id>', methods=['POST'])
@login_required
def delete_ct_request(req_id):
    req = CTRequest.query.get_or_404(req_id)
    if req.user_id != current_user.id and not current_user.has_role('admin'):
        flash('Operazione non autorizzata')
        return redirect(url_for('ct.ct_dashboard'))

    if current_user.has_role('admin') and req.status != 'rejected':
        flash("L'admin può eliminare solo richieste rifiutate")
        return redirect(url_for('ct.admin_ct_dashboard'))

    if req.status == 'approved' and req.user_id == current_user.id:
        flash('Impossibile eliminare una CT approvata')
        return redirect(url_for('ct.ct_dashboard'))

    db.session.delete(req)
    db.session.commit()
    flash('Richiesta eliminata')
    if current_user.has_role('admin'):
        return redirect(url_for('ct.admin_ct_dashboard'))

    return redirect(url_for('ct.ct_dashboard'))


@app.route('/access/<int:req_id>')
@login_required
def ct_access_details(req_id):
    req = CTRequest.query.get_or_404(req_id)
    
    if req.user_id != current_user.id:
        flash('Accesso non autorizzato')
        return redirect(url_for('ct.ct_dashboard'))
    
    if req.status != 'approved':
        flash('Accesso non disponibile')
        return redirect(url_for('ct.ct_dashboard'))
    
    access = {
        'ip': req.ct_ip,
        'hostname': req.ct_hostname,
        'user': req.ct_user,
        'password': req.ct_password,
        'ct_vmid': req.ct_vmid,
        'req_id': req.id
    }
    
    return render_template('access_details.html', access=access) 


@app.route('/access/refresh/<int:req_id>', methods=['POST'])
@login_required
def refresh_ct_ip(req_id):
    req = CTRequest.query.get_or_404(req_id)
    if req.user_id != current_user.id:
        flash('Operazione non autorizzata')
        return redirect(url_for('ct.ct_dashboard'))

    if req.status != 'approved':
        flash('La CT non è disponibile per ottenere l\'IP')
        return redirect(url_for('ct.ct_access_details', req_id=req_id))

    if not req.ct_vmid:
        flash('CT ID non disponibile')
        return redirect(url_for('ct.ct_access_details', req_id=req_id))

    node_index = CT_TYPE_TO_NODE.get(req.machine_name)
    if node_index is None:
        flash('Impossibile determinare il nodo della CT')
        return redirect(url_for('ct.ct_access_details', req_id=req_id))

    host = PROXMOX_HOSTS[node_index]
    node = PROXMOX_NODES[node_index]
    ip = get_container_ip(host, node, req.ct_vmid, timeout=5)
    if ip:
        req.ct_ip = ip
        db.session.commit()
        flash('IP aggiornato')
    else:
        flash('Impossibile recuperare l\'IP, riprova più tardi')

    return redirect(url_for('ct.ct_access_details', req_id=req_id))

