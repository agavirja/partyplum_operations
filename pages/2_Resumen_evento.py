import streamlit as st
import pandas as pd
import re
import copy
import json
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
def data_event(id_event):
    db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    data          = pd.read_sql(f"SELECT * FROM partyplum.events WHERE id={id_event}" , con=db_connection)
    return data

@st.experimental_memo
def data_plans():
    db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    data          = pd.read_sql("SELECT * FROM partyplum.package WHERE available=1" , con=db_connection)
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
def data_event_client():
    db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    data          = pd.read_sql("SELECT id as id_event,client,contracted_package,event_day,theme,celebrated_name,celebrated_name2 FROM partyplum.events" , con=db_connection)
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

id_event = ''
args     = st.experimental_get_query_params()
if 'id_event' in args: 
    try:    id_event = int(args['id_event'][0])
    except: id_event = ''
else: id_event = ''

if id_event=='':
    data_clientes       = data_event_client()
    data_clientes.index = range(len(data_clientes))
    idd                 = data_clientes.index>=0
    with st.sidebar:
        clientfilter  = st.selectbox('Nombre del cliente',options=sorted(data_clientes['client'].unique()))
        idd           = (idd) & (data_clientes['client']==clientfilter)
        
        packagefilter = st.selectbox('Paquete contratado',options=sorted(data_clientes[idd]['contracted_package'].unique()))
        idd           = (idd) & (data_clientes['contracted_package']==packagefilter)

        temafilter = st.selectbox('Tema del evento',options=sorted(data_clientes[idd]['theme'].unique()))
        idd        = (idd) & (data_clientes['theme']==temafilter)

        celebratedfilter = st.selectbox('Nombre del celebrado',options=sorted(data_clientes[idd]['celebrated_name'].unique()))
        idd              = (idd) & (data_clientes['celebrated_name']==celebratedfilter)
        
        fechacelebracion = st.date_input('Filtro por fecha')
        idd              = (idd) & (data_clientes['event_day']>=fechacelebracion)

        if sum(idd)>0:
            id_event = data_clientes[idd]['id_event'].iloc[0]
        else: st.error('No se encontro el evento')

data         = pd.DataFrame()
checkvalues  = False
try:    data = data_event(id_event)
except: st.error('Es necesario un id del evento, ir a buscar evento')

if data.empty is False:
    #-------------------------------------------------------------------------#
    # Estructura de data
    try:    clientdata       = json.loads(data['clientdata'].iloc[0])
    except: clientdata       = []
    try:    purchase_order   = json.loads(data['purchase_order'].iloc[0])
    except: purchase_order   = []
    try:    labour_order     = json.loads(data['labour_order'].iloc[0])
    except: labour_order     = []
    try:    transport_order  = json.loads(data['transport_order'].iloc[0])
    except: transport_order  = []
    try:    peajes_order     = json.loads(data['peajes_order'].iloc[0])
    except: peajes_order     = []
    try:    bakery_order     = json.loads(data['bakery_order'].iloc[0])
    except: bakery_order     = []
    try:    additional_order = json.loads(data['additional_order'].iloc[0])
    except: additional_order = []
    try:    other_expenses   = json.loads(data['other_expenses'].iloc[0])
    except: other_expenses   = []
    try:    pagos            = json.loads(data['pagos'].iloc[0])
    except: pagos            = []
    try:    img_event        = data['img_event'].iloc[0]
    except: img_event        = ''

    clientdata_origen     = copy.deepcopy(clientdata)
    purchase_origen       = copy.deepcopy(purchase_order)
    labour_origen         = copy.deepcopy(labour_order)
    transport_origen      = copy.deepcopy(transport_order)
    peajes_origen         = copy.deepcopy(peajes_order)
    bakery_origen         = copy.deepcopy(bakery_order)
    additional_origen     = copy.deepcopy(additional_order)
    other_expenses_origen = copy.deepcopy(other_expenses)
    pagos_origen          = copy.deepcopy(pagos)

    #-------------------------------------------------------------------------#
    # Formulario inicial
    st.markdown('<p style="color: #BA5778;"><strong>Datos del cliente y el evento</strong><p>', unsafe_allow_html=True)
        
    fechaanticipo    = None
    fechaanticipo2   = None
    fechapagofinal   = None
    anticipo2        = 0
    pagofinal        = 0
    nombrefestejado2 = ''
    edadfestejado2   = None
    package          = data_plans()

    col1, col2, col3 = st.columns(3)
    with col1:
        cliente            = st.text_input('Cliente',value=clientdata["client"]) 
        paquete_contratado = st.text_input('Paquete',value=clientdata['contracted_package'])         
        valorpaquete       = st.text_input('Valor',value=f'${clientdata["package_value"]:,.0f}')
        valorpaquete       = Price.fromstring(valorpaquete).amount_float    
        tematica           = st.text_input('Temática',value=clientdata["theme"])    
        ocacioncelebracion = st.text_input('Ocasión de Celebración',value=clientdata["occasion_celebration"])
        nombrefestejado    = st.text_input('Nombre del festejado',value=clientdata["celebrated_name"]) 
        
        try:    edadfestejado = int(clientdata['celebrated_age'])
        except: edadfestejado = 0
        edadfestejado = st.number_input('Edad festejado',min_value=0,value=edadfestejado)
        if clientdata['celebrated_name2']!='' and len(clientdata['celebrated_name2'])>3:
            nombrefestejado2   = st.text_input('Nombre del festejado 2',value=clientdata["celebrated_name2"])
            try:    celebrated_age2 = int(clientdata['celebrated_age2'])
            except: celebrated_age2 = 0
            edadfestejado2     = st.number_input('Edad festejado 2',min_value=0,value=celebrated_age2)

    with col2:    
        direccion          = st.text_input('Dirección evento',value=clientdata["address"] )
        ciudad             = st.text_input('Ciudad',value=clientdata["city"] )
        id_city            = clientdata["id_city"]
        fecha              = st.date_input('Fecha celebracion',value=data["event_day"].iloc[0])
        iniciocelebracion  = st.text_input('Hora inicio celebración',value=clientdata["start_event"])
        horamontaje        = st.text_input('Hora de montaje',value=clientdata["setup_time"])
        fecha_recogida     = st.date_input('Fecha de recogida',value=data["date_pick_up"].iloc[0])
        hora_recogida      = st.text_input('Hora de recogida',value=clientdata["hour_pick_up"])
    
    with col3:
        anticipo       = st.text_input('Anticipo',value=f'${clientdata["anticipo"]:,.0f}')
        anticipo       = Price.fromstring(anticipo).amount_float
        if anticipo>0:
            fechaanticipo  = st.date_input('Fecha anticipo',value=data["fechaanticipo"].iloc[0])
            anticipo2      = st.text_input('Anticipo 2',value=f'${clientdata["anticipo2"]:,.0f}')
            anticipo2      = Price.fromstring(anticipo2).amount_float
            if anticipo2>0: fechaanticipo2 = st.date_input('Fecha anticipo 2',value=data["fechaanticipo2"].iloc[0])
            pagofinal      = st.text_input('Pago final',value=f'${clientdata["pagofinal"]:,.0f}')
            pagofinal      = Price.fromstring(pagofinal).amount_float
            if pagofinal>0: fechapagofinal = st.date_input('Fecha pago final',value=data["fechapagofinal"].iloc[0])
    
    id_package = package[package['package']==paquete_contratado.upper()]['id'].iloc[0]
    pagos = [{'name':'Anticipo','value':anticipo,'date':fechaanticipo},
             {'name':'Anticipo 2','value':anticipo2,'date':fechaanticipo2},
             {'name':'Pago final','value':pagofinal,'date':fechapagofinal}]

    principal_img = ''
    if 'principal_img' in clientdata: principal_img = clientdata['principal_img']
    
    #-------------------------------------------------------------------------#
    # Render del montaje
    st.write('---')
    st.markdown('<p style="color: #BA5778;"><strong>Render del montaje</strong><p>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
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
    #variables  = ["id", "date_insert", "city", "address", "event_day", "start_event", "setup_time", "theme", "contracted_package", "package_value", "client", "celebrated_name", "celebrated_age", "celebrated_name2", "celebrated_age2", "occasion_celebration", "date_pick_up", "hour_pick_up", "anticipo", "fechaanticipo", "anticipo2", "fechaanticipo2", "pagofinal", "fechapagofinal", "pago_realizado", "clientdata", "purchase_order", "labour_order", "transport_order", "peajes_order", "bakery_order", "additional_order", "pagos", "principal_img","img_event"]
    variables  = list(data)
    variables  = [x for x in variables if x in dataexport]
    dataexport = dataexport[variables]
    
    #-------------------------------------------------------------------------#
    # Imagenes del montaje
    st.write('---')
    st.markdown('<p style="color: #BA5778;"><strong>Imagenes del montaje</strong><p>', unsafe_allow_html=True)

    css_format = """
        <style>
          .event-card-left {
            width: 100%;
            height: 400px;
            overflow-y: scroll; /* enable vertical scrolling for the images */
            text-align: justify;
            display: inline-block;
            margin: 0px auto;
          }
    
          .event-block {
            width:30%;
            background-color: white;
            margin-bottom: 10px; 
      	    display: inline-block;
      	    float: left;
            margin-right: 10px; 
          }
    
          .event-image{
            flex: 1;
          }
    
          .caracteristicas-info {
            font-size: 16px;
            margin-bottom: 2px;
          }
          img{
            width:100%;
            height:160px;
            margin-bottom: 10px; 
          }
        </style>
    """
        
    if img_event is None: img_event = ''
    if img_event!='':
        imagenes = ''
        for image in [x.strip() for x in img_event.split('|')]:
            imagenes += f'''
                  <div class="event-block">
                    <div class="event-image">
                      <img src="{image}" alt="event image"">
                    </div> 
                  </div>
                  '''
                  
        texto = f"""
        <!DOCTYPE html>
        <html>
          <head>
          {css_format}
          </head>
          <body>
            <div class="event-card-left">
            {imagenes}
            </div>
          </body>
        </html>
            """
        texto = BeautifulSoup(texto, 'html.parser')
        st.markdown(texto, unsafe_allow_html=True)
                           
    showimg = True
    for i in range(15):
        col1, col2, col3 = st.columns(3)
        if showimg:
            showimg = False
            with col1:
                checkvalues = st.checkbox(f"Subir imagen {i+1}", value=False)
            if checkvalues:
                with col2:
                    image_file = st.file_uploader(f"Subir imagen {i+1} del montaje",label_visibility="hidden")
                    if image_file is not None:
                        principal_img = img2s3(image_file)
                        if isinstance(principal_img, str) and len(principal_img)>20:
                            if img_event=='': img_event = copy.deepcopy(principal_img)
                            else: img_event += f'|{principal_img}'
                            with col3:
                                st.image(principal_img,width=300)
                                showimg = True
    
    
    #-------------------------------------------------------------------------#
    # Otros gastos
    st.write('---')
    st.markdown('<p style="color: #BA5778;"><strong>Otros gastos no contemplados</strong><p>', unsafe_allow_html=True)

    other_expenses = []
    maxidcount = 0
    for i in other_expenses_origen:
        if 'total' in i and i['total']>0:
            id_codigo = i['id']
            maxidcount = max(maxidcount,id_codigo)
            col1, col2, col3, col4 = st.columns([1,1,1,3])
            with col1:
                nombregasto = st.text_input(f'Nombre del gasto {id_codigo}',value=f"{i['name']}")
            with col2:
                total = st.text_input(f'Valor del gasto {id_codigo}',value=f"${i['total']:,.0f}") 
                total = Price.fromstring(total).amount_float
            with col3:
                options = ["Party Plum","Cliente"]
                options.remove(i['expensestype'])
                options = [i['expensestype']]+options
                tipogasto = st.selectbox(f'Quien asume el gasto {id_codigo}',options=options)
            with col4:
                description = st.text_area(f'Descripción del gasto {id_codigo}',value=f"{i['description']}")
            if total>0: 
                showimg = True
                other_expenses.append({
                                'name':nombregasto,
                                'id':maxidcount,
                                'total':total,
                                'expensestype':tipogasto,
                                'description':description                
                    })              
    showimg = True
    for i in range(10):
        maxidcount += 1
        col1, col2, col3, col4 = st.columns([1,1,1,3])
        if showimg:
            showimg = False
            with col1:
                nombregasto = st.text_input(f'Nombre del gasto {maxidcount}',value='')
            with col2:
                total = st.text_input(f'Valor del gasto {maxidcount}',value='$0') 
                total = Price.fromstring(total).amount_float
            with col3:
                tipogasto = st.selectbox(f'Quien asume el gasto {maxidcount}',options=["Party Plum","Cliente"])
            with col4:
                description = st.text_area(f'Descripción del gasto {maxidcount}',value='')
            if total>0: 
                showimg = True
                other_expenses.append({
                                'name':nombregasto,
                                'id':maxidcount,
                                'total':total,
                                'expensestype':tipogasto,
                                'description':description                
                    })  
                    
    #-------------------------------------------------------------------------#
    # Modificar valores
    st.write('---')
    st.markdown('<p style="color: #BA5778;"><strong>Modificar valores</strong><p>', unsafe_allow_html=True)
    checkvalues = st.checkbox('Modificar valores', value=False)
    
if checkvalues and data.empty is False:

    #-------------------------------------------------------------------------#
    # Orden de compra
    st.write('---')
    st.markdown('<p style="color: #BA5778;"><strong> Orden de compra:</strong><p>', unsafe_allow_html=True)
    
    products       = data_products(category='BASIC',id_package=id_package)
    printdata      = data_products(category='PRINT',id_package=id_package)
    products       = products.append(printdata)
    
    providers      = data_providers(category='BASIC')
    printproviders = data_providers(category='PRINT')
    providers      = providers.append(printproviders)
    
    purchase_paso  = copy.deepcopy(purchase_origen)
    purchase_order = []
    
    idlist         = []
    for i in purchase_paso:
        i['checkitem'] = True
        idlist.append(i['id'])
        
    for i,items in products.iterrows():
        if items['id'] not in idlist:
            purchase_paso.append({
                'name':items['item'],
                'id':items['id'],
                'amount':items['amount_default'],
                'unit_value':items['unit_value_default'],
                'total':items['amount_default']*items['unit_value_default'],
                'providers':[],
                'description':'',
                'checkitem':False
                })
    
    for items in purchase_paso:
        idcodigo   = items['id']
        name       = items['name']
        amount     = items['amount']
        unit_value = items['unit_value']
        try: unit_value = float(unit_value)
        except: pass
        proveedor_vector  = copy.deepcopy(items['providers'])
        proveedor_default = copy.deepcopy(items['providers'])
        description       = ''
        if 'description' in items:
            description = items['description']
        checkitem = False
        if 'checkitem' in items: checkitem = items['checkitem'] 
        
        col1, col2, col3, col4, col5, col6 = st.columns([1,2,2,2,2,3])
        with col1: 
            check_products = st.checkbox(f'{name}', value=checkitem)
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
                    proveedor_vector += sorted(providers[idd]['name'].to_list())
                if proveedor_vector!=[]:
                    proveedor_vector = list(set(proveedor_vector))
                proveedor  = st.multiselect(f'Proveedor {name}',options=proveedor_vector,default=proveedor_default)
            if name.lower().strip()=='globos' or 'flores' in name.lower().strip():
                with col6:
                    description   = st.text_area(f'Pedido {name}',value=description)
                            
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
    
    #-------------------------------------------------------------------------#
    # Personal
    st.write('---')
    st.markdown('<p style="color: #BA5778;"><strong> Personal:</strong><p>', unsafe_allow_html=True)
    
    labour       = data_labour()
    labour_paso  = copy.deepcopy(labour_origen)
    labour_order = []
    idlist       = []
    for i in labour_paso:
        i['checkitem'] = True
        if 'recargo_distancia' not in i: i['recargo_distancia'] = 0
        idlist.append(i['id'])
        
    for i,items in labour.iterrows():
        if items['id'] not in idlist:
            labour_paso.append({
                'name':items['name'],
                'id':items['id'],
                'total':items['cost_by_event'],
                'recargo_distancia':0,
                'checkitem':False
                })
            
    recargototaldistancia = 0
    for items in labour_paso:
        idcodigo          = items['id']
        name              = items['name']
        cost_by_event     = items['total']
        recargo_distancia = items['recargo_distancia']
        try: cost_by_event = float(cost_by_event)
        except: pass
        checkitem = False
        if 'checkitem' in items: checkitem = items['checkitem'] 
        
        col1, col2, col3, col4 = st.columns([1,2,2,2])
        with col1: 
            check_labour = st.checkbox(f'{name}', value=checkitem)
        if check_labour:
            with col2:
                valorU = st.text_input(f'Valor {name}',value=f'${cost_by_event:,.0f}') 
                valorU = Price.fromstring(valorU).amount_float
            with col3:
                recargo_distancia = st.text_input(f'Recargo por distancia {name}',value=f'${recargo_distancia:,.0f}')
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
    
    
    #-------------------------------------------------------------------------#
    # Transporte
    st.write('---')
    st.markdown('<p style="color: #BA5778;"><strong> Costos de transporte:</strong><p>', unsafe_allow_html=True)
    
    
    transport_paso = copy.deepcopy(transport_origen)
    for i in transport_paso:
        if 'recargo_distancia' not in i:
            i['recargo_distancia'] = 0
            
    # Gasolina
    valorU_gasolina      = 0
    valorrecargogasolina = 0
    
    if transport_paso!=[]:
        if 'total' in transport_paso[0]:
            valorU_gasolina = transport_paso[0]['total']
        if 'recargo_distancia' in transport_paso[0]:
            valorrecargogasolina = transport_paso[0]['recargo_distancia']
            
    checkitem = False
    if valorU_gasolina>0 or valorrecargogasolina>0:
        checkitem = True
        
    col1, col2, col3, col4 = st.columns([1,2,2,2])
    with col1:
        check_item = st.checkbox('Gasolina', value=checkitem)
        if check_item:
            with col2: 
                valorTotal_gasolina = st.text_input('Valor Gasolina',value=f'${valorU_gasolina:,.0f}') 
                valorU_gasolina     = Price.fromstring(valorTotal_gasolina).amount_float
            with col3:
                valorrecargogasolina = st.text_input('Valor recargo de Gasolina',value=f'${valorrecargogasolina:,.0f}') 
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
    peajes_paso = copy.deepcopy(peajes_origen)
    for i in peajes_paso:
        if 'recargo_distancia' not in i:
            i['recargo_distancia'] = 0
        
    valorTotal_Peajes = 0
    if peajes_paso!=[]:
        if 'recargo_distancia' in peajes_paso[0]:
            valorTotal_Peajes = peajes_paso[0]['recargo_distancia']
            
    checkitem = False
    if valorTotal_Peajes>0:
        checkitem = True
        
    if valorTotal_Peajes>0:
        col1, col2, col3, col4 = st.columns([1,2,2,2])
        with col1:
            check_item = st.checkbox('Peajes', value=checkitem)
            if check_item:
                with col2: 
                    valorTotal_Peajes     = st.text_input('Valor Peajes',value=f'${valorTotal_Peajes:,.0f}') 
                    valorTotal_Peajes     = Price.fromstring(valorTotal_Peajes).amount_float
                    recargototaldistancia += valorTotal_Peajes
                with col3:
                    st.text('Los peajes ni el recargo por distancia se descuenta de las ganancias')
    peajes_order = [{'name':'Peajes','total':0,'recargo_distancia':valorTotal_Peajes}]
                     
    st.markdown(f'<p style="color: #BA5778; font-size:12px;"><strong> Subtotal gastos de transporte ${transporte_suma:,.0f}</strong><p>', unsafe_allow_html=True)
    
    #-------------------------------------------------------------------------#
    # Reposteria
    st.write('---')
    st.markdown('<p style="color: #BA5778;"><strong> Repostería:</strong><p>', unsafe_allow_html=True)
    
    bakery_paso = copy.deepcopy(bakery_origen)
    checkitem   = False
    if  bakery_paso is not None and bakery_paso!=[]: checkitem = True
        
    check_item   = st.checkbox('Se incluye repostería?', value=checkitem)
    bakery_order = []
    bakery_suma  = 0
    
    if check_item:
        bakery    = data_products(category='BAKERY',id_package=id_package)
        providers = data_providers(category='BAKERY')    
        idlist    = []
        for i in bakery_paso:
            i['checkitem'] = True
            idlist.append(i['id'])
            
        for i,items in bakery.iterrows():
            if items['id'] not in idlist:
                bakery_paso.append({
                    'name':items['item'],
                    'id':items['id'],
                    'amount':items['amount_default'],
                    'unit_value':items['unit_value_default'],
                    'total':items['amount_default']*items['unit_value_default'],
                    'providers':[],
                    'description':'',
                    'checkitem':False
                    })
        
        for items in bakery_paso:
            idcodigo    = items['id']
            name        = items['name']
            amount      = items['amount']
            unit_value  = items['unit_value']
            try:    amount = int(amount)
            except: amount = 0
            try:    unit_value = float(unit_value)
            except: unit_value = 0
            
            proveedor_vector  = copy.deepcopy(items['providers'])
            proveedor_default = copy.deepcopy(items['providers'])
            description       = ''
            if 'description' in items:
                description = items['description']
            checkitem = False
            if 'checkitem' in items: checkitem = items['checkitem'] 
            
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            with col1:
                check_item  = st.checkbox(f'{name}', value=checkitem)
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
                        proveedor_vector += sorted(providers[idd]['name'].to_list())
                    if proveedor_vector!=[]:
                        proveedor_vector = list(set(proveedor_vector))
                    proveedor  = st.multiselect(f'Proveedor {name}',options=proveedor_vector,default=proveedor_default)
                if 'ponque' in name.lower().strip() or 'shots' in name.lower().strip():
                    with col6:
                        description   = st.text_area(f'Sabores {name}',value=description)
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
    
    #-------------------------------------------------------------------------#
    # Proovedores de reposteria
    for i in bakery_order:
        if 'providers' in i:
            if  len(i['providers'])>1:
                st.write('---')
                st.markdown('<p style="color: #BA5778;"><strong> Valor por proveedores de repostería:</strong><p>', unsafe_allow_html=True)
                break
    
    for i in bakery_order:
        for j in bakery_paso:
            if ('id' in i and 'id' in j) and (i['id'] is not None and j['id'] is not None) and int(i['id'])==int(j['id']):
                if 'provider_by_value' not in i: i['provider_by_value'] = []
                if 'provider_by_value' in j:
                    i['provider_by_value'] = copy.deepcopy(j['provider_by_value'])
                    break
    
    for i in bakery_order:
        if 'providers' in i:
            if len(i['providers'])>1:
                if 'total' in i and i['total']>0:
                    item   = ' '.join(i['name'].split('_')).title()
                    conteo = 1
                    proveedor_update     = []
                    suma_valor_proveedor = 0
                    col1, col2, col3 = st.columns(3)
                    with col1: 
                        st.write(item)
                    for nombre in i['providers']:
                        with col2:
                            nombre_proveedor = st.text_input(f'{item} proveedor {conteo}',value=f'{nombre}')
                        with col3:
                            value = 0
                            if 'provider_by_value' in i and i['provider_by_value'] is not None and i['provider_by_value']!=[]:
                                for pbv in i['provider_by_value']:
                                    if pbv['providers_name'].lower().strip()==nombre.lower().strip():
                                        if 'providers_value' in pbv:
                                            value = pbv['providers_value']
                                            break
         
                            valor_proveedor  = st.text_input(f'{item} proveedor {conteo} Valor',value=f'${value:,.0f}')
                            valor_proveedor  = Price.fromstring(valor_proveedor).amount_float                        
                            suma_valor_proveedor += valor_proveedor
                        proveedor_update.append({'providers_name':nombre_proveedor,'providers_value':valor_proveedor})
                        conteo += 1
                    i.update({'provider_by_value':proveedor_update})
                    
            if len(i['providers'])==1:
                col1, col2, col3 = st.columns(3)
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
                    proveedor_update = [{'providers_name':i['providers'][0],'providers_value':valor_proveedor}]
                    i.update({'provider_by_value':proveedor_update})
    
    #-------------------------------------------------------------------------#
    # Adicionales
    st.write('---')
    st.markdown('<p style="color: #BA5778;"><strong> Adicionales:</strong><p>', unsafe_allow_html=True)
    
    
    additional_paso = copy.deepcopy(additional_origen)
    additionalcheck = False
    if additional_paso is not None and additional_paso!=[]:
        additionalcheck = True
        for i in additional_paso:
            if i['name']=='Repostería':
                i['id'] = None
                i['total'] = bakery_suma
            if i['name']=='transporte fuera de la ciudad':
                i['total'] = recargototaldistancia
                
    check_item       = st.checkbox('Se incluyen adicionales?', value=additionalcheck)
    additional_order = []
    additional_suma  = 0
    
    if check_item:
        additional = data_products(category='ADDITIONAL',id_package=id_package)
        providers  = data_providers(category='ADDITIONAL')
        idlist     = []
        for i in additional_paso:
            i['checkitem'] = True
            if 'providers' not in i: i['providers'] = []
            idlist.append(i['id'])
            
        for i,items in additional.iterrows():
            if items['id'] not in idlist:
                additional_paso.append({
                    'name':items['item'],
                    'id':items['id'],
                    'amount':items['amount_default'],
                    'total':0,
                    'providers':[],
                    'description':'',
                    'checkitem':False
                    })
                
        for items in additional_paso:
            idcodigo = items['id']
            name     = items['name']
            proveedor_vector  = copy.deepcopy(items['providers'])
            proveedor_default = copy.deepcopy(items['providers'])
            description       = ''
            if 'description' in items:
                description = items['description']
            checkitem = False
            if 'checkitem' in items:    checkitem = items['checkitem'] 
            if name.lower().strip()=='transporte fuera de la ciudad' and recargototaldistancia>0: checkitem = True
            
            col1, col2, col3 = st.columns(3)
            with col1:
                check_item  = st.checkbox(f'{name}', value=checkitem)
            if  check_item:
                with col2:
                    value = items['total']
                    if name.lower().strip()=='transporte fuera de la ciudad' and recargototaldistancia>0:
                        value = copy.deepcopy(recargototaldistancia)
                    total = st.text_input(f'Valor {name}',value=f'${value:,.0f}')
                    total = Price.fromstring(total).amount_float
                with col3:
                    idd = providers['id']==idcodigo
                    if sum(idd)>0:
                        proveedor_vector += sorted(providers[idd]['name'].to_list())
                    if proveedor_vector!=[]:
                        proveedor_vector = list(set(proveedor_vector))
                    proveedor  = st.multiselect(f'Proveedor {name}',options=proveedor_vector,default=proveedor_default)
    
                additional_order.append({'name':name,
                                         'id':idcodigo,
                                         'total':total,
                                         'providers':proveedor})
        
        additional_suma = 0
        for i in additional_order:
            if 'total' in i: 
                additional_suma += i['total']
    st.markdown(f'<p style="color: #BA5778; font-size:12px;"><strong> Subtotal adicionales (incluye repostería) ${additional_suma:,.0f}</strong><p>', unsafe_allow_html=True)
    
    
    #-------------------------------------------------------------------------#
    # Proovedores de adicionales
    for i in additional_order:
        if 'providers' in i:
            if  len(i['providers'])>1:
                st.write('---')
                st.markdown('<p style="color: #BA5778;"><strong> Valor por proveedores de adicionales:</strong><p>', unsafe_allow_html=True)
                break
    
    for i in additional_order:
        for j in additional_paso:
            if ('id' in i and 'id' in j) and (i['id'] is not None and j['id'] is not None) and int(i['id'])==int(j['id']):
                if 'provider_by_value' not in i: i['provider_by_value'] = []
                if 'provider_by_value' in j:
                    i['provider_by_value'] = copy.deepcopy(j['provider_by_value'])
                    break
    
    for i in additional_order:
        if 'providers' in i:
            if len(i['providers'])>1:
                if 'total' in i and i['total']>0:
                    item   = ' '.join(i['name'].split('_')).title()
                    conteo = 1
                    proveedor_update     = []
                    suma_valor_proveedor = 0
                    col1, col2, col3 = st.columns(3)
                    with col1: 
                        st.write(item)
                    for nombre in i['providers']:
                        with col2:
                            nombre_proveedor = st.text_input(f'{item} proveedor {conteo}',value=f'{nombre}')
                        with col3:
                            value = 0
                            if 'provider_by_value' in i and i['provider_by_value'] is not None and i['provider_by_value']!=[]:
                                for pbv in i['provider_by_value']:
                                    if pbv['providers_name'].lower().strip()==nombre.lower().strip():
                                        if 'providers_value' in pbv:
                                            value = pbv['providers_value']
                                            break
         
                            valor_proveedor  = st.text_input(f'{item} proveedor {conteo} Valor',value=f'${value:,.0f}')
                            valor_proveedor  = Price.fromstring(valor_proveedor).amount_float                        
                            suma_valor_proveedor += valor_proveedor
                        proveedor_update.append({'providers_name':nombre_proveedor,'providers_value':valor_proveedor})
                        conteo += 1
                    i.update({'provider_by_value':proveedor_update})
                    
            if len(i['providers'])==1:
                col1, col2, col3 = st.columns(3)
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
                    proveedor_update = [{'providers_name':i['providers'][0],'providers_value':valor_proveedor}]
                    i.update({'provider_by_value':proveedor_update})
                    
if data.empty is False:
    #-------------------------------------------------------------------------#
    # Resumen
    
    orden_suma = 0
    for i in purchase_order:
        if 'total' in i and i['total']>0: 
            orden_suma += i['total']
            
    personal_suma = 0
    for i in labour_order:
        if 'total' in i and i['total']>0: 
            personal_suma += i['total']

    transporte_suma = 0
    for i in transport_order:
        if 'total' in i and i['total']>0: 
            transporte_suma += i['total'] 
            
    bakery_suma = 0
    for i in bakery_order:
        if 'total' in i and i['total']>0: 
            bakery_suma += i['total']
         
    additional_suma = 0
    for i in additional_order:
        if 'total' in i and i['total']>0 : 
            additional_suma += i['total']
        
    other_expenses_partyplum_suma = 0
    other_expenses_cliente_suma   = 0
    for i in other_expenses:
        if 'total' in i and i['total']>0:
            if 'expensestype' in i:
                if i['expensestype'].lower()=="party plum":
                    other_expenses_partyplum_suma += i['total']
                if i['expensestype'].lower()=="cliente":
                    other_expenses_cliente_suma += i['total']            
    
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
        
    # Otros gastos       
    if other_expenses!=[]:
        st.write('---')
        st.markdown('<p><strong>Otros gastos</strong><p>', unsafe_allow_html=True)
        count = 0
        tabla = '''
            <tr>
                <th>Concepto</th>
                <th>Valor total</th>
                <th>Quien asume el gasto</th>
                <th>Descripcion</th>
            </tr>
        '''
        
        for i in other_expenses:
            if count % 2 == 0:
                color = "dcdcdc"
            else:
                color = "FF94F4"
            tabla += f'''
              <tr style="background-color: #{color};">
                <td style="font-family:{fontfamily};font-size:{fontsize}px;">{i['name']}</td>
                <td style="font-family:{fontfamily};font-size:{fontsize}px;">${i['total']:,.0f}</td>
                <td style="font-family:{fontfamily};font-size:{fontsize}px;">{i['expensestype']}</td>
                <td style="font-family:{fontfamily};font-size:{fontsize}px;">{i['description']}</td>
              </tr>
            '''
            count += 1
            
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
    st.markdown('<p><strong> Cuentas generales</strong><p>', unsafe_allow_html=True)
    gastototalfijos = orden_suma+personal_suma+transporte_suma+other_expenses_partyplum_suma
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
        st.markdown('<p><strong> Repostería</strong><p>', unsafe_allow_html=True)
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
        st.markdown('<p><strong> Adicionales</strong><p>', unsafe_allow_html=True)
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
    for i in other_expenses:
        if 'total' in i and i['total']>0:
            if 'expensestype' in i:
                if i['expensestype'].lower()=="cliente":
                    tabla_adicionales += f'''
                      <tr style="background-color: #ffffff;">
                        <td style="font-family:{fontfamily};font-size:{fontsize}px; border: 1px solid black;">{i['name']}</td>
                        <td style="font-family:{fontfamily};font-size:{fontsize}px; border: 1px solid black;">${i['total']:,.0f}</td>
                      </tr>
                    '''
    tabla_adicionales += f'''
      <tr style="background-color: #FFFFFF;">
        <td style="font-family:{fontfamily};font-size:{fontsize}px; background-color: #FF94F4; border: 1px solid black;"><strong>Total</strong></td>
        <td style="font-family:{fontfamily};font-size:{fontsize}px; background-color: #FF94F4; border: 1px solid black;"><strong>${valorpaquete+additional_suma+other_expenses_cliente_suma:,.0f}</strong></td>
      </tr>
    '''
      
    # Estado de cuenta
    total_pagos = 0
    for i in pagos:
        if 'value' in i and i['value']>0:
            total_pagos += i['value']
        
    saldo_pendiente = valorpaquete+additional_suma+other_expenses_cliente_suma-total_pagos
    
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
                dataexport.index                     = range(len(dataexport))
                dataexport['date_insert']            = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                dataexport.loc[0,'purchase_order']   = pd.io.json.dumps(purchase_order)
                dataexport.loc[0,'labour_order']     = pd.io.json.dumps(labour_order)
                dataexport.loc[0,'transport_order']  = pd.io.json.dumps(transport_order)
                dataexport.loc[0,'peajes_order']     = pd.io.json.dumps(peajes_order)
                dataexport.loc[0,'bakery_order']     = pd.io.json.dumps(bakery_order)
                dataexport.loc[0,'additional_order'] = pd.io.json.dumps(additional_order)
                dataexport.loc[0,'other_expenses']   = pd.io.json.dumps(other_expenses)
                dataexport.loc[0,'pagos']            = pd.io.json.dumps(pagos)
                dataexport.loc[0,'clientdata']       = pd.io.json.dumps(clientdata)
                dataexport.loc[0,'img_event']        = img_event

                # Guardar una copia en datos historicos
                data2historic              = copy.deepcopy(dataexport)
                data2historic['id_events'] = id_event

                engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
                data2historic.to_sql('events_historic',engine,if_exists='append', index=False)
                
                # Reemplazar datos en la base de datos de eventos
                variables = ''
                varlist   = []
                for i in dataexport:
                    if dataexport[i].iloc[0] is not None and dataexport[i].iloc[0]!='':
                        variables += f',{i}=%s'
                        varlist.append(i)
                        
                variables        = variables.strip(',').strip()
                data2event       = dataexport[varlist]
                data2event['id'] = id_event
                valores          = list(data2event.apply(lambda x: tuple(x), axis=1).unique())
                db_connection = sql.connect(user=user, password=password, host=host, database=schema)
                cursor        = db_connection.cursor()
                cursor.executemany(f"""UPDATE {schema}.events SET {variables} WHERE id=%s """,valores)
                db_connection.commit()
                db_connection.close()
                
                st.success('Datos guardados con exito')
                
                time.sleep(3)
                st.experimental_memo.clear()
                st.experimental_rerun()