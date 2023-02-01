import streamlit as st
import json
import pandas as pd
import re
import copy
import tempfile
import mysql.connector as sql
import boto3
import random
import time
from datetime import datetime
from bs4 import BeautifulSoup
from sqlalchemy import create_engine 
from price_parser import Price
import pdfcrowd

st.set_page_config(layout="wide")

user     = st.secrets["user"]
password = st.secrets["password"]
host     = st.secrets["host"]
schema   = st.secrets["schema"]
pdfcrowduser = st.secrets["pdfcrowduser"]
pdfcrowdpass = st.secrets["pdfcrowdpass"]

@st.experimental_memo
def data_plans():
    db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    data          = pd.read_sql("SELECT * FROM partyplum.package WHERE available=1" , con=db_connection)
    return data

@st.experimental_memo
def data_city():
    db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    data          = pd.read_sql("SELECT id as id_city,ciudad FROM partyplum.city" , con=db_connection)
    return data

@st.experimental_memo
def data_products(category,id_package):
    db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    data          = pd.read_sql(f"SELECT id_item as id, item, amount_default, unit_value_default  FROM partyplum.products_package WHERE  available=1 AND category='{category}' AND id_package={id_package}" , con=db_connection)
    return data

@st.experimental_memo
def data_providers(category):
    db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    data          = pd.read_sql(f"SELECT id_item as id, name  FROM partyplum.providers WHERE available=1 AND category='{category}' " , con=db_connection)
    return data

@st.experimental_memo
def data_labour():
    db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    data          = pd.read_sql("SELECT id, name, cost_by_event  FROM partyplum.labour WHERE available=1" , con=db_connection)
    return data

@st.experimental_memo
def data_event():
    db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    data          = pd.read_sql("SELECT * FROM partyplum.events LIMIT 1" , con=db_connection)
    return data

@st.experimental_memo
def data_event_client():
    db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    data          = pd.read_sql("SELECT client,clientdata,event_day,date_pick_up FROM partyplum.events" , con=db_connection)
    return data

@st.experimental_memo
def img2s3(image_file):
    principal_img =  "https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/sin_imagen.png"
    session = boto3.Session(
        aws_access_key_id=st.secrets["aws_access_key_id"],
        aws_secret_access_key=st.secrets["aws_secret_access_key"],
        region_name=st.secrets["region_name"]
    )
    try:
        #s3 = boto3.client("s3")
        s3 = session.client('s3')
        randomnumber = str(random.uniform(0,100)).replace('.','')[:10]
        images3name  = f'partyplum_{randomnumber}.png' 
        s3file       = f'partyplum/{images3name}'
        s3.upload_fileobj(
            image_file,
            'personal-data-bucket-online',
            s3file,
            ExtraArgs={
                "ContentType": "image/png"
            }
        )
        principal_img = f'https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/{s3file}'
    except: pass
    return principal_img
    
#-----------------------------------------------------------------------------#
# Datos del cliente
st.markdown('<p style="color: #BA5778;"><strong>Datos del cliente y el evento</strong><p>', unsafe_allow_html=True)

fechaanticipo    = None
fechaanticipo2   = None
fechapagofinal   = None
anticipo2        = 0
pagofinal        = 0
nombrefestejado2 = ''
edadfestejado2   = None
package          = data_plans()
data_form        = data_event_client()
data_ciudad      = data_city()

col1, col2, col3 = st.columns(3)
with col1:

    if data_form.empty is False: 
        valueclient = sorted(data_form['client'].unique())+['NUEVO CLIENTE']
        cliente     = st.selectbox('Cliente',options=valueclient)
        if cliente=='NUEVO CLIENTE':
            cliente = st.text_input('Nombre del cliente',value='')
    else: cliente = st.text_input('Cliente',value='')
    
    # Opciones
    paquete_contratado_options = [x.title() for x in package['package']]       
    tematica_options           = ''
    ocacioncelebracion_options = ['CUMPLEAÑOS','PRIMERA COMUNIÓN','BAUTIZO','GRADO','BABY SHOWER','QUINCEAÑERA','DESPEDIDA DE SOLTERO(A)','SHOWER']
    nombrefestejado_options    = ''
    edadfestejado_options      = 0
    direccion_options          = ''
    ciudad_options             = data_ciudad['ciudad'].to_list()
    iniciocelebracion_options  = ["07:00 AM", "07:30 AM", "08:00 AM", "08:30 AM", "09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM", "11:00 AM", "11:30 AM", "12:00 PM", "12:30 PM", "01:00 PM", "01:30 PM", "02:00 PM", "02:30 PM", "03:00 PM", "03:30 PM", "04:00 PM", "04:30 PM", "05:00 PM", "05:30 PM", "06:00 PM", "06:30 PM", "07:00 PM", "07:30 PM", "08:00 PM", "08:30 PM", "09:00 PM", "09:30 PM", "10:00 PM", "10:30 PM", "11:00 PM", "11:30 PM"]
    hora_recogida_options      = ["07:00 AM", "07:30 AM", "08:00 AM", "08:30 AM", "09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM", "11:00 AM", "11:30 AM", "12:00 PM", "12:30 PM", "01:00 PM", "01:30 PM", "02:00 PM", "02:30 PM", "03:00 PM", "03:30 PM", "04:00 PM", "04:30 PM", "05:00 PM", "05:30 PM", "06:00 PM", "06:30 PM", "07:00 PM", "07:30 PM", "08:00 PM", "08:30 PM", "09:00 PM", "09:30 PM", "10:00 PM", "10:30 PM", "11:00 PM", "11:30 PM"]
    
    idd = data_form['client']==cliente
    if sum(idd)>0:
        preform = json.loads(data_form[idd]['clientdata'].iloc[0])
        try:
            paquete_contratado_options.remove(preform['contracted_package'])
            paquete_contratado_options = [preform['contracted_package']]+paquete_contratado_options
        except: paquete_contratado_options = [preform['contracted_package']]
        try:
            ocacioncelebracion_options.remove(preform['occasion_celebration'])
            ocacioncelebracion_options = [preform['occasion_celebration']]+ocacioncelebracion_options
        except: ocacioncelebracion_options = [preform['occasion_celebration']]
        try:
            ciudad_options.remove(preform['city'])
            ciudad_options  = [preform['city']] + ciudad_options
        except: ciudad_options = [preform['city']]
        try:
            iniciocelebracion_options.remove(preform['start_event'])
            iniciocelebracion_options =  [preform['start_event']] + iniciocelebracion_options
        except: iniciocelebracion_options = [preform['start_event']]
        try:
            hora_recogida_options.remove(preform['hour_pick_up'])
            hora_recogida_options = [preform['hour_pick_up']] + hora_recogida_options
        except: hora_recogida_options = [preform['hour_pick_up']]
        
        event_day_option        = data_form[idd]['event_day'].iloc[0]
        date_pick_up_option     = data_form[idd]['date_pick_up'].iloc[0]
        tematica_options        = preform['theme']
        nombrefestejado_options = preform['celebrated_name']
        edadfestejado_options   = preform['celebrated_age']
        direccion_options       = preform['address']
        
    paquete_contratado = st.selectbox('Paquete',options=paquete_contratado_options)         
    valorpaquete       = package[package['package']==paquete_contratado.upper()]['price'].iloc[0]
    valorpaquete       = st.text_input('Valor',value=f'${valorpaquete:,.0f}')
    valorpaquete       = Price.fromstring(valorpaquete).amount_float    
    tematica           = st.text_input('Temática',value=tematica_options)    
    ocacioncelebracion = st.selectbox('Ocasión de Celebración',options=ocacioncelebracion_options)
    nombrefestejado    = st.text_input('Nombre del festejado',value=nombrefestejado_options) 
    edadfestejado      = st.number_input('Edad festejado',min_value=0,value=edadfestejado_options)
    if st.checkbox('Otro festejado', value=False):
        nombrefestejado2 = st.text_input('Nombre del festejado 2',value='')
        edadfestejado2   = st.number_input('Edad festejado 2',min_value=0)
    
with col2:
    direccion          = st.text_input('Dirección evento',value=direccion_options)
    ciudad             = st.selectbox('Ciudad',options=ciudad_options)
    id_city            = data_ciudad[data_ciudad['ciudad']==ciudad]['id_city'].iloc[0]
    try:    fecha      = st.date_input('Fecha celebracion',value=event_day_option)
    except: fecha      = st.date_input('Fecha celebracion')
    iniciocelebracion  = st.selectbox('Hora inicio celebración',options=iniciocelebracion_options)
    horamontaje        = st.selectbox('Hora de montaje',options=["07:00 AM", "07:30 AM", "08:00 AM", "08:30 AM", "09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM", "11:00 AM", "11:30 AM", "12:00 PM", "12:30 PM", "01:00 PM", "01:30 PM", "02:00 PM", "02:30 PM", "03:00 PM", "03:30 PM", "04:00 PM", "04:30 PM", "05:00 PM", "05:30 PM", "06:00 PM", "06:30 PM", "07:00 PM", "07:30 PM", "08:00 PM", "08:30 PM", "09:00 PM", "09:30 PM", "10:00 PM", "10:30 PM", "11:00 PM", "11:30 PM"],key=2)
    try:    fecha_recogida = st.date_input('Fecha de recogida',value=date_pick_up_option)
    except: fecha_recogida = st.date_input('Fecha de recogida',value=fecha)
    hora_recogida      = st.selectbox('Hora de recogida',options=["07:00 AM", "07:30 AM", "08:00 AM", "08:30 AM", "09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM", "11:00 AM", "11:30 AM", "12:00 PM", "12:30 PM", "01:00 PM", "01:30 PM", "02:00 PM", "02:30 PM", "03:00 PM", "03:30 PM", "04:00 PM", "04:30 PM", "05:00 PM", "05:30 PM", "06:00 PM", "06:30 PM", "07:00 PM", "07:30 PM", "08:00 PM", "08:30 PM", "09:00 PM", "09:30 PM", "10:00 PM", "10:30 PM", "11:00 PM", "11:30 PM"],key=18)

with col3:
    anticipo           = st.text_input('Anticipo',value='$0')
    anticipo           = Price.fromstring(anticipo).amount_float
    if anticipo>0:
        fechaanticipo  = st.date_input('Fecha anticipo')
        anticipo2      = st.text_input('Anticipo 2',value='$0')
        anticipo2      = Price.fromstring(anticipo2).amount_float
        if anticipo2>0: fechaanticipo2 = st.date_input('Fecha anticipo 2')
        pagofinal      = st.text_input('Pago final',value='$0')
        pagofinal      = Price.fromstring(pagofinal).amount_float
        if pagofinal>0: fechapagofinal = st.date_input('Fecha pago final')

id_package = package[package['package']==paquete_contratado.upper()]['id'].iloc[0]
pagos = [{'name':'Anticipo','value':anticipo,'date':fechaanticipo},
         {'name':'Anticipo 2','value':anticipo2,'date':fechaanticipo2},
         {'name':'Pago final','value':pagofinal,'date':fechapagofinal}]

try: iniciocelebracion = str(iniciocelebracion)
except: pass 


#-----------------------------------------------------------------------------#
# Render del montaje
st.write('---')
st.markdown('<p style="color: #BA5778;"><strong>Render del montaje</strong><p>', unsafe_allow_html=True)
col1, col2 = st.columns(2)
principal_img = "https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/sin_imagen.png"
with col1:
    image_file = st.file_uploader("Subir render del montaje",label_visibility="hidden")
    if image_file is not None:
        principal_img = img2s3(image_file)

if principal_img!='':
    with col2:
        st.image(principal_img,width=300)

# Data Cliente Total
clientdata = {'city':ciudad,
              'id_city':id_city,
              'address':direccion,
              'event_day':fecha,
              'start_event':iniciocelebracion,
              'setup_time':horamontaje,
              'theme':tematica.upper(),
              'contracted_package':paquete_contratado,
              'package_value':valorpaquete,
              'client':cliente.upper(),
              'celebrated_name':nombrefestejado.upper(),
              'celebrated_age':edadfestejado,
              'celebrated_name2':nombrefestejado2.upper(),
              'celebrated_age2':edadfestejado2,
              'occasion_celebration':ocacioncelebracion.upper(),
              'date_pick_up':fecha_recogida,
              'hour_pick_up':hora_recogida,
              'principal_img':principal_img,
              'anticipo':anticipo,
              'fechaanticipo':fechaanticipo,
              'anticipo2':anticipo2,
              'fechaanticipo2':fechaanticipo2,
              'pagofinal':pagofinal,
              'fechapagofinal':fechapagofinal
              } 

dataexport = pd.DataFrame([clientdata])
dataevents = data_event()
#variables  = ["id", "date_insert", "city","id_city","address", "event_day", "start_event", "setup_time", "theme", "contracted_package", "package_value", "client", "celebrated_name", "celebrated_age", "celebrated_name2", "celebrated_age2", "occasion_celebration", "date_pick_up", "hour_pick_up", "anticipo", "fechaanticipo", "anticipo2", "fechaanticipo2", "pagofinal", "fechapagofinal", "pago_realizado", "clientdata", "purchase_order", "labour_order", "transport_order", "peajes_order", "bakery_order", "additional_order", "pagos", "principal_img","img_event"]
variables  = [x for x in list(dataevents) if x in dataexport]
dataexport = dataexport[variables]

#-----------------------------------------------------------------------------#
# Orden de compra
st.write('---')
st.markdown('<p style="color: #BA5778;"><strong> Orden de compra:</strong><p>', unsafe_allow_html=True)

products       = data_products(category='BASIC',id_package=id_package)
providers      = data_providers(category='BASIC')
purchase_order = []

for i,items in products.iterrows():
    idcodigo   = items['id']
    name       = items['item']
    amount     = items['amount_default']
    unit_value = items['unit_value_default']
    try: unit_value = float(unit_value)
    except: pass
    proveedor   = []
    description = ''
    #col1, col2, col3, col4, col5, col6 = st.columns([1,2,2,2,2,3])
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1: 
        check_products = st.checkbox(f'{name}', value=True)
    if check_products:
        with col2:
            cantidad = st.number_input(f'Cantidad {name}',min_value=0,value=amount)
        with col3:
            valorU   = st.text_input(f'Valor unitario {name}',value=f'${unit_value:,.0f}')
            valorU   = Price.fromstring(valorU).amount_float
        with col4:
            total          = cantidad*valorU
            valorTotal_str = st.text_input(f'Valor Total {name}',value=f'${total:,.0f}')
        with col5:
            idd = providers['id']==idcodigo
            if sum(idd)>0:
                proveedor  = st.multiselect(f'Proveedor {name}',options=sorted(providers[idd]['name'].to_list()))
        if name.lower().strip()=='globos' or 'flores' in name.lower().strip() :
            with col6:
                description   = st.text_input(f'Pedido {name}',value='')
                        
        purchase_order.append({'name':name,
                               'id':idcodigo,
                               'amount':cantidad,
                               'unit_value':valorU,
                               'total':total,
                               'providers':proveedor,
                               'description':description})
orden_suma = 0
for i in purchase_order:
    if 'total' in i: 
        orden_suma += i['total']
st.markdown(f'<p style="color: #BA5778; font-size:12px;"><strong> Subtotal orden de pedido ${orden_suma:,.0f}</strong><p>', unsafe_allow_html=True)

#-----------------------------------------------------------------------------#
# Proovedores orden de compra
for i in purchase_order:
    if 'providers' in i:
        if  len(i['providers'])>1:
            st.write('---')
            st.markdown('<p style="color: #BA5778;"><strong> Valor por proveedores de orden de compra:</strong><p>', unsafe_allow_html=True)
            break
for i in purchase_order:
    if 'providers' in i:
        if len(i['providers'])>1:
            if 'total' in i and i['total']>0:
                k      = int(int(i['total'])/len(i['providers']))
                item   = ' '.join(i['name'].split('_')).title()
                conteo = 1
                proveedor_update     = []
                suma_valor_proveedor = 0
                col1, col2, col3, col4 = st.columns(4)
                with col1: 
                    st.write(item)
                for nombre in i['providers']:
                    with col2:
                        nombre_proveedor = st.text_input(f'{item} proveedor {conteo}',value=f'{nombre}')
                    with col3:
                        valor_proveedor  = st.text_input(f'{item} proveedor {conteo} Valor',value=f'${int(k):,.0f}')
                        valor_proveedor  = Price.fromstring(valor_proveedor).amount_float
                        suma_valor_proveedor += valor_proveedor
                    proveedor_update.append({'providers_name':nombre_proveedor,'providers_value':valor_proveedor})
                    conteo += 1
                with col4:
                    st.write(f"Valor total {item}: ${i['total']:,.0f}")
                    if suma_valor_proveedor>i['total']:
                        st.error(f"Valor de proveedores de {item} mayor a ${i['total']:,.0f}")
                    elif suma_valor_proveedor<i['total']:
                        st.error(f"Valor de proveedores de {item} menor a ${i['total']:,.0f}")    
                    else:
                        st.success("Las cuentas cuadran bien")
                i.update({'provider_by_value':proveedor_update})
                
        if len(i['providers'])==1:
            col1, col2, col3, col4 = st.columns(4)
            with col1: 
                item   = ' '.join(i['name'].split('_')).title()
                st.write(item)
            with col2:
                nombre_proveedor = st.text_input(f'{item} proveedor',value=f"{i['providers'][0]}")
            with col3:
                valor_proveedor  = st.text_input(f'{item} proveedor Valor',value=f"${i['total']:,.0f}")
                valor_proveedor  = Price.fromstring(valor_proveedor).amount_float
                    
            if 'total' in i and i['total']>0:
                item             = ' '.join(i['name'].split('_')).title()
                proveedor_update = [{'providers_name':i['providers'][0],'providers_value':i['total']}]
                i.update({'provider_by_value':proveedor_update})
    
#-----------------------------------------------------------------------------#
# Impresiones
st.write('---')
st.markdown('<p style="color: #BA5778;"><strong>Imptresiones:</strong><p>', unsafe_allow_html=True)

check_item      = st.checkbox('Se incluye impresiones a medida?', value=False)
printinfo_order = []
printinfo_suma  = 0

if check_item:
    printinfo = data_products(category='PRINT',id_package=id_package)
    providers = data_providers(category='PRINT')
    for i,items in printinfo.iterrows():
        idcodigo    = items['id']
        name        = items['item']
        amount      = items['amount_default']
        unit_value  = items['unit_value_default']
        description = ''
        try:    amount = int(amount)
        except: amount = 0
        try:    unit_value = float(unit_value)
        except: unit_value = 0
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            check_item  = st.checkbox(f'{name}', value=False)
        if  check_item:
            with col2:
                cantidad = st.number_input(f'Cantidad {name}',min_value=0,value=amount)
            with col3:
                valorU   = st.text_input(f'Valor unitario {name}',value=f'${unit_value:,.0f}')
                valorU   = Price.fromstring(valorU).amount_float
            with col4:
                total          = cantidad*valorU
                valorTotal_str = st.text_input(f'Valor Total {name}',value=f'${total:,.0f}')
            with col5:
                idd = providers['id']==idcodigo
                if sum(idd)>0:
                    proveedor  = st.multiselect(f'Proveedor {name}',options=sorted(providers[idd]['name'].to_list()))
            if 'ponque' in name.lower().strip() or 'shots' in name.lower().strip():
                with col6:
                    description   = st.text_input(f'Sabores {name}',value='')
            printinfo_order.append({'name':name,
                                    'id':idcodigo,
                                    'amount':cantidad,
                                    'unit_value':valorU,
                                    'total':total,
                                    'providers':proveedor,
                                    'description':description})
    printinfo_suma = 0
    for i in printinfo_order:
        if 'total' in i: 
            printinfo_suma += i['total']
    st.markdown(f'<p style="color: #BA5778; font-size:12px;"><strong> Subtotal repostería ${printinfo_suma:,.0f}</strong><p>', unsafe_allow_html=True)

    orden_suma = orden_suma + printinfo_suma
#-----------------------------------------------------------------------------#
# Proovedores de impresiones
for i in printinfo_order:
    if 'providers' in i:
        if  len(i['providers'])>1:
            st.write('---')
            st.markdown('<p style="color: #BA5778;"><strong> Valor por proveedores de repostería:</strong><p>', unsafe_allow_html=True)
            break

for i in printinfo_order:
    if 'providers' in i:
        if len(i['providers'])>1:
            if 'total' in i and i['total']>0:
                k      = int(int(i['total'])/len(i['providers']))
                item   = ' '.join(i['name'].split('_')).title()
                conteo = 1
                proveedor_update     = []
                suma_valor_proveedor = 0
                col1, col2, col3, col4 = st.columns(4)
                with col1: 
                    st.write(item)
                for nombre in i['providers']:
                    with col2:
                        nombre_proveedor = st.text_input(f'{item} proveedor {conteo}',value=f'{nombre}')
                    with col3:
                        valor_proveedor  = st.text_input(f'{item} proveedor {conteo} Valor',value=f'${int(k):,.0f}')
                        valor_proveedor  = Price.fromstring(valor_proveedor).amount_float                        
                        suma_valor_proveedor += valor_proveedor
                    proveedor_update.append({'providers_name':nombre_proveedor,'providers_value':valor_proveedor})
                    conteo += 1
                with col4:
                    st.write(f"Valor total {item}: ${i['total']:,.0f}")
                    if suma_valor_proveedor>i['total']:
                        st.error(f"Valor de proveedores de {item} mayor a ${i['total']:,.0f}")
                    elif suma_valor_proveedor<i['total']:
                        st.error(f"Valor de proveedores de {item} menor a ${i['total']:,.0f}")    
                    else:
                        st.success("Las cuentas cuadran bien")
                i.update({'provider_by_value':proveedor_update})
                
        if len(i['providers'])==1:
            col1, col2, col3, col4 = st.columns(4)
            with col1: 
                item   = ' '.join(i['name'].split('_')).title()
                st.write(item)
            with col2:
                nombre_proveedor = st.text_input(f'{item} proveedor',value=f"{i['providers'][0]}")
            with col3:
                valor_proveedor  = st.text_input(f'{item} proveedor Valor',value=f"${i['total']:,.0f}")
                valor_proveedor  = Price.fromstring(valor_proveedor).amount_float
                
            if 'total' in i and i['total']>0:
                item             = ' '.join(i['name'].split('_')).title()
                proveedor_update = [{'providers_name':i['providers'][0],'providers_value':i['total']}]
                i.update({'provider_by_value':proveedor_update})

# Impresiones va en la parte de basicos
purchase_order = purchase_order + printinfo_order

  
#-----------------------------------------------------------------------------#
# Personal
st.write('---')
st.markdown('<p style="color: #BA5778;"><strong> Personal:</strong><p>', unsafe_allow_html=True)

labour       = data_labour()
labour_order = []
recargototaldistancia = 0
for i,items in labour.iterrows():
    idcodigo      = items['id']
    name          = items['name']
    cost_by_event = items['cost_by_event']
    try: cost_by_event = float(cost_by_event)
    except: pass
    #col1, col2, col3, col4 = st.columns([1,2,2,2])
    col1, col2, col3, col4 = st.columns(4)
    with col1: 
        check_labour = st.checkbox(f'{name}', value=False)
    if check_labour:
        with col2:
            valorU = st.text_input(f'Valor {name}',value=f'${cost_by_event:,.0f}') 
            valorU = Price.fromstring(valorU).amount_float
        with col3:
            recargo_distancia = st.text_input(f'Recargo por distancia {name}',value='$0')
            recargo_distancia = Price.fromstring(recargo_distancia).amount_float
            recargototaldistancia += recargo_distancia
        with col4:
            valorTotalP = st.text_input(f'Valor total con recargo {name}',value=f'${valorU+recargo_distancia:,.0f}') 
            
        labour_order.append({
                            'name':name,
                            'id':idcodigo,
                            'total':valorU,
                            'recargo_distancia':recargo_distancia
                            })
personal_suma = 0
for i in labour_order:
    if 'total' in i: 
        personal_suma += i['total']
st.markdown(f'<p style="color: #BA5778; font-size:12px;"><strong> Subtotal personal ${personal_suma:,.0f}</strong><p>', unsafe_allow_html=True)

#-----------------------------------------------------------------------------#
# Transporte
st.write('---')
st.markdown('<p style="color: #BA5778;"><strong> Costos de transporte:</strong><p>', unsafe_allow_html=True)

# Gasolina
valorU_gasolina      = 30000
valorrecargogasolina = 0
col1, col2, col3, col4 = st.columns([1,2,2,2])
with col1:
    check_item = st.checkbox('Gasolina', value=False)
    if check_item:
        with col2: 
            valorTotal_gasolina = st.text_input('Valor Gasolina',value=f'${valorU_gasolina:,.0f}') 
            valorU_gasolina     = Price.fromstring(valorTotal_gasolina).amount_float
        with col3:
            valorrecargogasolina = st.text_input('Valor recargo de Gasolina',value='$0') 
            valorrecargogasolina = Price.fromstring(valorrecargogasolina).amount_float            
            recargototaldistancia += valorrecargogasolina
        with col4: 
            valorTotalG = st.text_input('Valor total con recargo Gasolina',value=f'${valorU_gasolina+valorrecargogasolina:,.0f}') 
transport_order = [{'name':'Gasolina','total':valorU_gasolina,'recargo_distancia':valorrecargogasolina}]

transporte_suma = 0
for i in transport_order:
    if 'total' in i: 
        transporte_suma += i['total']   

# Peajes
valorTotal_Peajes = 0
if recargototaldistancia>0:
    col1, col2, col3, col4 = st.columns([1,2,2,2])
    with col1:
        check_item = st.checkbox('Peajes', value=False)
        if check_item:
            with col2: 
                valorTotal_Peajes     = st.text_input('Valor Peajes',value=f'${valorTotal_Peajes:,.0f}') 
                valorTotal_Peajes     = Price.fromstring(valorTotal_Peajes).amount_float
                recargototaldistancia += valorTotal_Peajes
            with col3:
                st.text('Los peajes ni el recargo por distancia se descuenta de las ganancias')
peajes_order = [{'name':'Peajes','total':0,'recargo_distancia':valorTotal_Peajes}]
                 
st.markdown(f'<p style="color: #BA5778; font-size:12px;"><strong> Subtotal gastos de transporte ${transporte_suma:,.0f}</strong><p>', unsafe_allow_html=True)


#-----------------------------------------------------------------------------#
# Reposteria
st.write('---')
st.markdown('<p style="color: #BA5778;"><strong> Repostería:</strong><p>', unsafe_allow_html=True)

check_item   = st.checkbox('Se incluye repostería?', value=False)
bakery_order = []
bakery_suma  = 0

if check_item:
    bakery    = data_products(category='BAKERY',id_package=id_package)
    providers = data_providers(category='BAKERY')
    for i,items in bakery.iterrows():
        idcodigo    = items['id']
        name        = items['item']
        amount      = items['amount_default']
        unit_value  = items['unit_value_default']
        description = ''
        try:    amount = int(amount)
        except: amount = 0
        try:    unit_value = float(unit_value)
        except: unit_value = 0
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            check_item  = st.checkbox(f'{name}', value=False)
        if  check_item:
            with col2:
                cantidad = st.number_input(f'Cantidad {name}',min_value=0,value=amount)
            with col3:
                valorU   = st.text_input(f'Valor unitario {name}',value=f'${unit_value:,.0f}')
                valorU   = Price.fromstring(valorU).amount_float
            with col4:
                total          = cantidad*valorU
                valorTotal_str = st.text_input(f'Valor Total {name}',value=f'${total:,.0f}')
            with col5:
                idd = providers['id']==idcodigo
                if sum(idd)>0:
                    proveedor  = st.multiselect(f'Proveedor {name}',options=sorted(providers[idd]['name'].to_list()))
            if 'ponque' in name.lower().strip() or 'shots' in name.lower().strip():
                with col6:
                    description   = st.text_input(f'Sabores {name}',value='')
            bakery_order.append({'name':name,
                                    'id':idcodigo,
                                    'amount':cantidad,
                                    'unit_value':valorU,
                                    'total':total,
                                    'providers':proveedor,
                                    'description':description})
    bakery_suma = 0
    for i in bakery_order:
        if 'total' in i: 
            bakery_suma += i['total']
    st.markdown(f'<p style="color: #BA5778; font-size:12px;"><strong> Subtotal repostería ${bakery_suma:,.0f}</strong><p>', unsafe_allow_html=True)

#-----------------------------------------------------------------------------#
# Proovedores de reposteria
for i in bakery_order:
    if 'providers' in i:
        if  len(i['providers'])>1:
            st.write('---')
            st.markdown('<p style="color: #BA5778;"><strong> Valor por proveedores de repostería:</strong><p>', unsafe_allow_html=True)
            break

for i in bakery_order:
    if 'providers' in i:
        if len(i['providers'])>1:
            if 'total' in i and i['total']>0:
                k      = int(int(i['total'])/len(i['providers']))
                item   = ' '.join(i['name'].split('_')).title()
                conteo = 1
                proveedor_update     = []
                suma_valor_proveedor = 0
                col1, col2, col3, col4 = st.columns(4)
                with col1: 
                    st.write(item)
                for nombre in i['providers']:
                    with col2:
                        nombre_proveedor = st.text_input(f'{item} proveedor {conteo}',value=f'{nombre}')
                    with col3:
                        valor_proveedor  = st.text_input(f'{item} proveedor {conteo} Valor',value=f'${int(k):,.0f}')
                        valor_proveedor  = Price.fromstring(valor_proveedor).amount_float                        
                        suma_valor_proveedor += valor_proveedor
                    proveedor_update.append({'providers_name':nombre_proveedor,'providers_value':valor_proveedor})
                    conteo += 1
                with col4:
                    st.write(f"Valor total {item}: ${i['total']:,.0f}")
                    if suma_valor_proveedor>i['total']:
                        st.error(f"Valor de proveedores de {item} mayor a ${i['total']:,.0f}")
                    elif suma_valor_proveedor<i['total']:
                        st.error(f"Valor de proveedores de {item} menor a ${i['total']:,.0f}")    
                    else:
                        st.success("Las cuentas cuadran bien")
                i.update({'provider_by_value':proveedor_update})
                
        if len(i['providers'])==1:
            col1, col2, col3, col4 = st.columns(4)
            with col1: 
                item   = ' '.join(i['name'].split('_')).title()
                st.write(item)
            with col2:
                nombre_proveedor = st.text_input(f'{item} proveedor',value=f"{i['providers'][0]}")
            with col3:
                valor_proveedor  = st.text_input(f'{item} proveedor Valor',value=f"${i['total']:,.0f}")
                valor_proveedor  = Price.fromstring(valor_proveedor).amount_float
                
            if 'total' in i and i['total']>0:
                item             = ' '.join(i['name'].split('_')).title()
                proveedor_update = [{'providers_name':i['providers'][0],'providers_value':i['total']}]
                i.update({'provider_by_value':proveedor_update})
    
    
#-----------------------------------------------------------------------------#
# Adicionales
st.write('---')
st.markdown('<p style="color: #BA5778;"><strong> Adicionales:</strong><p>', unsafe_allow_html=True)

additionalcheck = False
if recargototaldistancia>0:
    additionalcheck = True
    
check_item       = st.checkbox('Se incluyen adicionales?', value=additionalcheck)
additional_order = []
additional_suma = 0

if bakery_suma>0:
    additional_order.append({'name':'Repostería',
                             'id':None,
                             'total':bakery_suma})
if check_item:
    additional = data_products(category='ADDITIONAL',id_package=id_package)
    providers  = data_providers(category='ADDITIONAL')
    for i,items in additional.iterrows():
        idcodigo = items['id']
        name     = items['item']
        col1, col2, col3 = st.columns(3)
        with col1:
            additionalcheck = False
            if name.lower().strip()=='transporte fuera de la ciudad' and recargototaldistancia>0:
                additionalcheck = True
                
            check_item  = st.checkbox(f'{name}', value=additionalcheck)
        if  check_item:
            with col2:
                value = 0
                if name.lower().strip()=='transporte fuera de la ciudad' and recargototaldistancia>0:
                    value = copy.deepcopy(recargototaldistancia)
                total = st.text_input(f'Valor {name}',value=f'${value:,.0f}')
                total = Price.fromstring(total).amount_float
            with col3:
                idd = providers['id']==idcodigo
                if sum(idd)>0:
                    proveedor  = st.multiselect(f'Proveedor {name}',options=sorted(providers[idd]['name'].to_list()))

            additional_order.append({'name':name,
                                     'id':idcodigo,
                                     'total':total,
                                     'providers':proveedor})
    
    additional_suma = 0
    for i in additional_order:
        if 'total' in i: 
            additional_suma += i['total']
st.markdown(f'<p style="color: #BA5778; font-size:12px;"><strong> Subtotal adicionales (incluye repostería) ${additional_suma:,.0f}</strong><p>', unsafe_allow_html=True)

#-----------------------------------------------------------------------------#
# Proovedores de adicionales
for i in additional_order:
    if 'providers' in i:
        if  len(i['providers'])>1:
            st.write('---')
            st.markdown('<p style="color: #BA5778;"><strong> Valor por proveedores de adicionales:</strong><p>', unsafe_allow_html=True)
            break

for i in additional_order:
    if 'providers' in i:
        if len(i['providers'])>1:
            if 'total' in i and i['total']>0:
                k      = int(int(i['total'])/len(i['providers']))
                item   = ' '.join(i['name'].split('_')).title()
                conteo = 1
                proveedor_update     = []
                suma_valor_proveedor = 0
                col1, col2, col3, col4 = st.columns(4)
                with col1: 
                    st.write(item)
                for nombre in i['providers']:
                    with col2:
                        nombre_proveedor = st.text_input(f'{item} proveedor {conteo}',value=f'{nombre}')
                    with col3:
                        valor_proveedor  = st.text_input(f'{item} proveedor {conteo} Valor',value=f'${int(k):,.0f}')
                        valor_proveedor  = Price.fromstring(valor_proveedor).amount_float
                        suma_valor_proveedor += valor_proveedor
                    proveedor_update.append({'providers_name':nombre_proveedor,'providers_value':valor_proveedor})
                    conteo += 1
                with col4:
                    st.write(f"Valor total {item}: ${i['total']:,.0f}")
                    if suma_valor_proveedor>i['total']:
                        st.error(f"Valor de proveedores de {item} mayor a ${i['total']:,.0f}")
                    elif suma_valor_proveedor<i['total']:
                        st.error(f"Valor de proveedores de {item} menor a ${i['total']:,.0f}")    
                    else:
                        st.success("Las cuentas cuadran bien")
                i.update({'provider_by_value':proveedor_update})
                
        if len(i['providers'])==1:
            col1, col2, col3, col4 = st.columns(4)
            with col1: 
                item   = ' '.join(i['name'].split('_')).title()
                st.write(item)
            with col2:
                nombre_proveedor = st.text_input(f'{item} proveedor',value=f"{i['providers'][0]}")
            with col3:
                valor_proveedor  = st.text_input(f'{item} proveedor Valor',value=f"${i['total']:,.0f}")
                valor_proveedor  = Price.fromstring(valor_proveedor).amount_float
                
            if 'total' in i and i['total']>0:
                item             = ' '.join(i['name'].split('_')).title()
                proveedor_update = [{'providers_name':i['providers'][0],'providers_value':i['total']}]
                i.update({'provider_by_value':proveedor_update})
                
#-----------------------------------------------------------------------------#
# Resumen
st.write('---')
st.markdown('<p style="color: #BA5778;"><strong>Resumen:</strong><p>', unsafe_allow_html=True)

fontsize        = 13
fontfamily      = 'sans-serif'
backgroundcolor = '#FAFAFA'

css_format = """
  <style>
    .resumen {
      width: 100%;
      margin-left: 10px;
      text-align: justify;
    }
  </style>
"""

# Orden de compra
if purchase_order!=[]:
    st.markdown('<p><strong>Orden de compra</strong><p>', unsafe_allow_html=True)
    count = 0
    tabla = '''
        <tr>
            <th>Producto</th>
            <th>Cantidad</th>
            <th>Valor total</th>
        </tr>
    '''
    
    for i in purchase_order:
        if count % 2 == 0:
            color = "dcdcdc"
        else:
            color = "FF94F4"
        tabla += f'''
          <tr style="background-color: #{color};">
            <td style="font-family:{fontfamily};font-size:{fontsize}px;">{i['name']}</td>
            <td style="font-family:{fontfamily};font-size:{fontsize}px;">{i['amount']}</td>
            <td style="font-family:{fontfamily};font-size:{fontsize}px;">${i['total']:,.0f}</td>
          </tr>
        '''
        count += 1
    
    # Total
    tabla += f'''
      <tr style="background-color: #FFFFFF;">
        <td style="font-family:{fontfamily};font-size:{fontsize}px;"><strong>Total</strong></td>
        <td style="font-family:{fontfamily};font-size:{fontsize}px;"></td>
        <td style="font-family:{fontfamily};font-size:{fontsize}px;"><strong>${orden_suma:,.0f}</strong></td>
      </tr>
    '''
    
    if tabla!="":
        tabla = f'''
        <ul>
            <table style="width:100%;">
            {tabla}
            </table>
        </ul>
        '''
    html_struct = f"""
    <!DOCTYPE html>
    <html>
    <head>
    {css_format}
    </head>
    <body>
    <div class="resumen">
    {tabla}
    </div>
    </body>
    </html>
    """
    html_struct = BeautifulSoup(html_struct, 'html.parser')
    st.markdown(html_struct, unsafe_allow_html=True)

# Personal
if labour_order!=[]:
    st.write('---')
    st.markdown('<p><strong>Personal</strong><p>', unsafe_allow_html=True)
    count = 0
    tabla = '''
        <tr>
            <th>Nombre</th>
            <th>Valor total</th>
        </tr>
    '''
    
    for i in labour_order:
        if count % 2 == 0:
            color = "dcdcdc"
        else:
            color = "FF94F4"
        tabla += f'''
          <tr style="background-color: #{color};">
            <td style="font-family:{fontfamily};font-size:{fontsize}px;">{i['name']}</td>
            <td style="font-family:{fontfamily};font-size:{fontsize}px;">${i['total']:,.0f}</td>
          </tr>
        '''
        count += 1
    
    # Totales
    tabla += f'''
      <tr style="background-color: #FFFFFF;">
        <td style="font-family:{fontfamily};font-size:{fontsize}px;"><strong>Total</strong></td>
        <td style="font-family:{fontfamily};font-size:{fontsize}px;"><strong>${personal_suma:,.0f}</strong></td>
      </tr>
    '''
    if tabla!="":
        tabla = f'''
        <ul>
            <table style="width:100%;">
            {tabla}
            </table>
        </ul>
        '''
    html_struct = f"""
    <!DOCTYPE html>
    <html>
    <head>
    {css_format}
    </head>
    <body>
    <div class="resumen">
    {tabla}
    </div>
    </body>
    </html>
    """
    html_struct = BeautifulSoup(html_struct, 'html.parser')
    st.markdown(html_struct, unsafe_allow_html=True)

# Transporte
if transport_order!=[]:
    st.write('---')
    st.markdown('<p><strong>Transporte</strong><p>', unsafe_allow_html=True)
    count = 0
    tabla = '''
        <tr>
            <th>Descripcion</th>
            <th>Valor total</th>
        </tr>
    '''
    
    for i in transport_order:
        if count % 2 == 0:
            color = "dcdcdc"
        else:
            color = "FF94F4"
        tabla += f'''
          <tr style="background-color: #{color};">
            <td style="font-family:{fontfamily};font-size:{fontsize}px;">{i['name']}</td>
            <td style="font-family:{fontfamily};font-size:{fontsize}px;">${i['total']:,.0f}</td>
          </tr>
        '''
        count += 1
        
    # Totales
    tabla += f'''
      <tr style="background-color: #FFFFFF;">
        <td style="font-family:{fontfamily};font-size:{fontsize}px;"><strong>Total</strong></td>
        <td style="font-family:{fontfamily};font-size:{fontsize}px;"><strong>${transporte_suma:,.0f}</strong></td>
      </tr>
    '''
    if tabla!="":
        tabla = f'''
        <ul>
            <table style="width:100%;">
            {tabla}
            </table>
        </ul>
        '''
    html_struct = f"""
    <!DOCTYPE html>
    <html>
    <head>
    {css_format}
    </head>
    <body>
    <div class="resumen">
    {tabla}
    </div>
    </body>
    </html>
    """
    html_struct = BeautifulSoup(html_struct, 'html.parser')
    st.markdown(html_struct, unsafe_allow_html=True)
    
    
# Cuentas generales
st.write('---')
st.markdown('<p><strong>Cuentas generales</strong><p>', unsafe_allow_html=True)
gastototalfijos = orden_suma+personal_suma+transporte_suma
ganancia = valorpaquete-gastototalfijos
tabla = f'''
    <ul>
        <table style="width:100%;">
            <tr>
                <th>Valor paquete</th>
                <th>Total Gastos Fijos</th>
                <th>Ganancia</th>
            </tr>
            <tr style="background-color: #FFFFFF;">
                <td style="font-family:{fontfamily};font-size:{fontsize}px;"><strong>${valorpaquete:,.0f}</strong></td>
                <td style="font-family:{fontfamily};font-size:{fontsize}px;">${gastototalfijos:,.0f}</td>
                <td style="font-family:{fontfamily};font-size:{fontsize}px;"><strong>${ganancia:,.0f}</strong></td>
            </tr>
        </table>
    </ul>
'''

html_struct = f"""
<!DOCTYPE html>
<html>
<head>
{css_format}
</head>
<body>
<div class="resumen">
{tabla}
</div>
</body>
</html>
"""
html_struct = BeautifulSoup(html_struct, 'html.parser')
st.markdown(html_struct, unsafe_allow_html=True)    


# Reposteria
if bakery_order!=[]:
    st.write('---')
    st.markdown('<p><strong>Repostería</strong><p>', unsafe_allow_html=True)
    count = 0
    tabla = '''
        <tr>
            <th>Producto</th>
            <th>Cantidad</th>
            <th>Valor total</th>
        </tr>
    '''
    
    for i in bakery_order:
        if count % 2 == 0:
            color = "dcdcdc"
        else:
            color = "FF94F4"
        tabla += f'''
          <tr style="background-color: #{color};">
            <td style="font-family:{fontfamily};font-size:{fontsize}px;">{i['name']+' '+i['description']}</td>
            <td style="font-family:{fontfamily};font-size:{fontsize}px;">{i['amount']}</td>
            <td style="font-family:{fontfamily};font-size:{fontsize}px;">${i['total']:,.0f}</td>
          </tr>
        '''
        count += 1
    
    # Total
    tabla += f'''
      <tr style="background-color: #FFFFFF;">
        <td style="font-family:{fontfamily};font-size:{fontsize}px;"><strong>Total</strong></td>
        <td style="font-family:{fontfamily};font-size:{fontsize}px;"></td>
        <td style="font-family:{fontfamily};font-size:{fontsize}px;"><strong>${bakery_suma:,.0f}</strong></td>
      </tr>
    '''
    
    if tabla!="":
        tabla = f'''
        <ul>
            <table style="width:100%;">
            {tabla}
            </table>
        </ul>
        '''
    html_struct = f"""
    <!DOCTYPE html>
    <html>
    <head>
    {css_format}
    </head>
    <body>
    <div class="resumen">
    {tabla}
    </div>
    </body>
    </html>
    """
    html_struct = BeautifulSoup(html_struct, 'html.parser')
    st.markdown(html_struct, unsafe_allow_html=True)

# Adicionales
if additional_order!=[]:
    st.write('---')
    st.markdown('<p><strong>Adicionales</strong><p>', unsafe_allow_html=True)
    count = 0
    tabla = '''
        <tr>
            <th>Producto</th>
            <th>Valor total</th>
        </tr>
    '''
    
    for i in additional_order:
        if count % 2 == 0:
            color = "dcdcdc"
        else:
            color = "FF94F4"
        tabla += f'''
          <tr style="background-color: #{color};">
            <td style="font-family:{fontfamily};font-size:{fontsize}px;">{i['name']}</td>
            <td style="font-family:{fontfamily};font-size:{fontsize}px;">${i['total']:,.0f}</td>
          </tr>
        '''
        count += 1
    
    # Total
    tabla += f'''
      <tr style="background-color: #FFFFFF;">
        <td style="font-family:{fontfamily};font-size:{fontsize}px;"><strong>Total</strong></td>
        <td style="font-family:{fontfamily};font-size:{fontsize}px;"><strong>${additional_suma:,.0f}</strong></td>
      </tr>
    '''
    
    if tabla!="":
        tabla = f'''
        <ul>
            <table style="width:100%;">
            {tabla}
            </table>
        </ul>
        '''
    html_struct = f"""
    <!DOCTYPE html>
    <html>
    <head>
    {css_format}
    </head>
    <body>
    <div class="resumen">
    {tabla}
    </div>
    </body>
    </html>
    """
    html_struct = BeautifulSoup(html_struct, 'html.parser')
    st.markdown(html_struct, unsafe_allow_html=True)
    
#-----------------------------------------------------------------------------#
# Pantallazo para el cliente
st.write('---')
st.markdown('<p style="color: #BA5778;"><strong> Resumen para el cliente</strong><p>', unsafe_allow_html=True)

# Reposteria
tabla_reposteria = ''
for i in bakery_order:
    tabla_reposteria += f'''
      <tr style="background-color: #ffffff;">
        <td style="font-family:{fontfamily};font-size:{fontsize}px; border: 1px solid black;">{i['name']+' '+i['description']}</td>
        <td style="font-family:{fontfamily};font-size:{fontsize}px; border: 1px solid black;">{i['amount']}</td>
        <td style="font-family:{fontfamily};font-size:{fontsize}px; border: 1px solid black;">${i['total']:,.0f}</td>
      </tr>
    '''
if tabla_reposteria!='': 
    tabla_reposteria += f'''
      <tr style="background-color: #FFFFFF;">
        <td style="font-family:{fontfamily};font-size:{fontsize}px; border: 1px solid black;"><strong>Total</strong></td>
        <td style="font-family:{fontfamily};font-size:{fontsize}px; border: 1px solid black;"></td>
        <td style="font-family:{fontfamily};font-size:{fontsize}px; border: 1px solid black;"><strong>${bakery_suma:,.0f}</strong></td>
      </tr>
    '''

# Adicionales
tabla_adicionales = f'''
  <tr style="background-color: #ffffff;">
    <td style="font-family:{fontfamily};font-size:{fontsize}px; border: 1px solid black;">Decoración {paquete_contratado}</td>
    <td style="font-family:{fontfamily};font-size:{fontsize}px; border: 1px solid black;">${valorpaquete:,.0f}</td>
  </tr>
'''
for i in additional_order:
    tabla_adicionales += f'''
      <tr style="background-color: #ffffff;">
        <td style="font-family:{fontfamily};font-size:{fontsize}px; border: 1px solid black;">{i['name']}</td>
        <td style="font-family:{fontfamily};font-size:{fontsize}px; border: 1px solid black;">${i['total']:,.0f}</td>
      </tr>
    '''
tabla_adicionales += f'''
  <tr style="background-color: #FFFFFF;">
    <td style="font-family:{fontfamily};font-size:{fontsize}px; background-color: #FF94F4; border: 1px solid black;"><strong>Total</strong></td>
    <td style="font-family:{fontfamily};font-size:{fontsize}px; background-color: #FF94F4; border: 1px solid black;"><strong>${valorpaquete+additional_suma:,.0f}</strong></td>
  </tr>
'''
  
# Estado de cuenta
total_pagos = 0
for i in pagos:
    if 'value' in i and i['value']>0:
        total_pagos += i['value']
    
saldo_pendiente = valorpaquete+additional_suma-total_pagos

tabla_pagos = ''
for i in pagos:
    if 'value' in i and i['value']>0:
        tabla_pagos += f'''
          <tr style="background-color: #ffffff;">
            <td style="font-family:{fontfamily};font-size:{fontsize}px; border: 1px solid black;">{i['name']}</td>
            <td style="font-family:{fontfamily};font-size:{fontsize}px; border: 1px solid black;">{i['date']}</td>
            <td style="font-family:{fontfamily};font-size:{fontsize}px; border: 1px solid black;">${i['value']:,.0f}</td>
          </tr>
        '''
tabla_pagos += f'''
  <tr style="background-color: #ffffff;">
    <td style="font-family:{fontfamily};font-size:{fontsize}px; border: 1px solid black; background-color: #61F1FC;">Saldo pendiente a cancelar</td>
    <td style="font-family:{fontfamily};font-size:{fontsize}px; border: 1px solid black; background-color: #61F1FC;"></td>
    <td style="font-family:{fontfamily};font-size:{fontsize}px; border: 1px solid black; background-color: #61F1FC;">${saldo_pendiente:,.0f}</td>
  </tr>
'''


css_format = """
  <style>
    .resumen {
      width: 60%;
      margin-left: 10px;
      text-align: justify;
    }
    img{
        width:400;
        height:180px;
        margin-bottom: 10px; 
    }
  </style>
"""

tabla = f'''
    <div style="text-align: center; background-color: white; border: 1px solid black;">
        <img src="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/partyplum_logosimbolo.png" style="display: block; margin: auto;">
    </div>
    <div>
    <ul>
        <table style="width:100%; margin-bottom: 30px; background-color: white; border: 1px solid black;">
          <tr style="background-color: #ffffff;">
              <td style="width:70%; font-family:{fontfamily};font-size:{fontsize}px; background-color: #FF94F4; border: 1px solid black;"><strong>{paquete_contratado}</strong></td>
              <td style="width:30%; font-family:{fontfamily};font-size:{fontsize}px; border: 1px solid black;"><strong>${valorpaquete:,.0f}</strong></td>
          </tr>
        </table>
        <table style="text-align: center; width:100%; background-color: white; border: 1px solid black;">
            <td style="font-family:{fontfamily};font-size:{fontsize}px; border: 1px solid black;"><strong>Adicionales Repostería</strong></td>
        </table>
        <table style="width:100%; margin-bottom: 30px; background-color: white; border: 1px solid black;">
            <tr>
                <th style="text-align: center; width:100%; background-color: white; border: 1px solid black; font-family:{fontfamily};font-size:{fontsize}px;">Producto</th>
                <th style="text-align: center; width:100%; background-color: white; border: 1px solid black; font-family:{fontfamily};font-size:{fontsize}px;">Cantidad</th>
                <th style="text-align: center; width:100%; background-color: white; border: 1px solid black; font-family:{fontfamily};font-size:{fontsize}px;">Valor</th>
            </tr>
            {tabla_reposteria}
        </table>
        <table style="text-align: center; width:100%; background-color: white; border: 1px solid black;">
            <td style="font-family:{fontfamily};font-size:{fontsize}px; background-color: #FF94F4; border: 1px solid black;"><strong>Resumen</strong></td>
        </table>
        <table style="width:100%; margin-bottom: 30px; background-color: white; border: 1px solid black;">
            <tr>
                <th style="text-align: center; width:100%; background-color: white; border: 1px solid black; font-family:{fontfamily};font-size:{fontsize}px;">Producto</th>
                <th style="text-align: center; width:100%; background-color: white; border: 1px solid black; font-family:{fontfamily};font-size:{fontsize}px;">Valor</th>
            </tr>
            {tabla_adicionales}
        </table>
        
        <table style="text-align: center; width:100%; background-color: white; border: 1px solid black;">
            <td style="font-family:{fontfamily};font-size:{fontsize}px; background-color: #D9D9D9; border: 1px solid black;"><strong>Estado de cuenta</strong></td>
        </table>
        <table style="width:100%; background-color: white; border: 1px solid black;">
            <tr>
                <th style="text-align: center; width:100%; background-color: white; border: 1px solid black; font-family:{fontfamily};font-size:{fontsize}px;">Tipo de pago</th>
                <th style="text-align: center; width:100%; background-color: white; border: 1px solid black; font-family:{fontfamily};font-size:{fontsize}px;">Fecha</th>
                <th style="text-align: center; width:100%; background-color: white; border: 1px solid black; font-family:{fontfamily};font-size:{fontsize}px;">Valor</th>
            </tr>
            {tabla_pagos}
        </table>
    </ul>
    </div> 
  
'''

html_struct = f"""
<!DOCTYPE html>
<html>
<head>
{css_format}
</head>
<body>
<div class="resumen">
{tabla}
</div>
</body>
</html>
"""
html_struct = BeautifulSoup(html_struct, 'html.parser')
st.markdown(html_struct, unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    if st.button('Generar pdf'):
        css_format = """
          <style>
            .resumen {
              width: 80%;
              margin-left: 10px;
              text-align: justify;
            }
            img{
                width:400;
                height:180px;
                margin-bottom: 10px; 
            }
          </style>
        """
        html_struct = f"""
        <!DOCTYPE html>
        <html>
        <head>
        {css_format}
        </head>
        <body>
        <div class="resumen">
        {tabla}
        </div>
        </body>
        </html>
        """
    
        caracteres_especiales = {
            "á": "&aacute;",
            "é": "&eacute;",
            "í": "&iacute;",
            "ó": "&oacute;",
            "ú": "&uacute;",
            "ñ": "&ntilde;",
            "Á": "&Aacute;",
            "É": "&Eacute;",
            "Í": "&Iacute;",
            "Ó": "&Oacute;",
            "Ú": "&Uacute;",
            "Ñ": "&Ntilde;",
        }
        for caracter, codigo in caracteres_especiales.items():
            html_struct = re.sub(caracter, codigo, html_struct)
                
        html_struct = BeautifulSoup(html_struct, 'html.parser')
        
        with st.spinner("Generando pdf"):
    
            fd, temp_path     = tempfile.mkstemp(suffix=".html")
            wd, pdf_temp_path = tempfile.mkstemp(suffix=".pdf")       
            
            client = pdfcrowd.HtmlToPdfClient(pdfcrowduser,pdfcrowdpass)
            client.convertStringToFile(html_struct, pdf_temp_path)

            with open(pdf_temp_path, "rb") as pdf_file:
                PDFbyte = pdf_file.read()
            
            st.download_button(label="Descargar PDF",
                                data=PDFbyte,
                                file_name="resumen_party_plum.pdf",
                                mime='application/octet-stream')

with col2:
    if st.button('Guardar Datos'):
        with st.spinner("Guardando Datos"):
            pagos.append({'name':'saldo_pendiente','value':saldo_pendiente,'date':None})
            pagos.append({'name':'valorpaquete','value':valorpaquete,'date':None})
            dataexport['date_insert']            = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            dataexport.loc[0,'purchase_order']   = pd.io.json.dumps(purchase_order)
            dataexport.loc[0,'labour_order']     = pd.io.json.dumps(labour_order)
            dataexport.loc[0,'transport_order']  = pd.io.json.dumps(transport_order)
            dataexport.loc[0,'peajes_order']     = pd.io.json.dumps(peajes_order)
            dataexport.loc[0,'bakery_order']     = pd.io.json.dumps(bakery_order)
            dataexport.loc[0,'additional_order'] = pd.io.json.dumps(additional_order)
            dataexport.loc[0,'other_expenses']   = pd.io.json.dumps([])
            dataexport.loc[0,'pagos']            = pd.io.json.dumps(pagos)
            dataexport.loc[0,'clientdata']       = pd.io.json.dumps(clientdata)
             
            engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
            dataexport.to_sql('events',engine,if_exists='append', index=False)
            
            db_connection = sql.connect(user=user, password=password, host=host, database=schema)
            lastid        = pd.read_sql("SELECT MAX(id) as id_event FROM partyplum.events" , con=db_connection)
            if lastid.empty is False:
                id_event = lastid['id_event'].iloc[0]
                dataexport['id_events'] = id_event
                
                engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
                dataexport.to_sql('events_historic',engine,if_exists='append', index=False)
            
            st.success('Datos guardados con exito')
            
            time.sleep(3)
            st.experimental_memo.clear()
            st.experimental_rerun()