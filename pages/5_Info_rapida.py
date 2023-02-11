import streamlit as st
import pandas as pd
import mysql.connector as sql
from price_parser import Price

st.set_page_config(layout="centered")

user     = st.secrets["user"]
password = st.secrets["password"]
host     = st.secrets["host"]
schema   = st.secrets["schema"]

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
    data          = pd.read_sql("SELECT id as id_event,client,contracted_package,event_day,theme,celebrated_name,celebrated_name2 FROM partyplum.events WHERE available=1" , con=db_connection)
    return data


data                = pd.DataFrame()
data_clientes       = data_event_client()
data_clientes.index = range(len(data_clientes))
idd                 = data_clientes.index>=0

col1, col2 = st.columns(2)
with col1:
    # Filtros
    clientfilter  = st.selectbox('Nombre del cliente',options=sorted(data_clientes['client'].unique()))
    idd           = (idd) & (data_clientes['client']==clientfilter)

with col2:
    packagefilter = st.selectbox('Paquete contratado',options=sorted(data_clientes[idd]['contracted_package'].unique()))
    idd           = (idd) & (data_clientes['contracted_package']==packagefilter)

col1, col2 = st.columns(2)
with col1:
    temafilter = st.selectbox('Tema del evento',options=sorted(data_clientes[idd]['theme'].unique()))
    idd        = (idd) & (data_clientes['theme']==temafilter)

with col2:
    celebratedfilter = st.selectbox('Nombre del celebrado',options=sorted(data_clientes[idd]['celebrated_name'].unique()))
    idd              = (idd) & (data_clientes['celebrated_name']==celebratedfilter)


if sum(idd)>0:
    id_event = data_clientes[idd]['id_event'].iloc[0]
    data     = data_event(id_event)

if data.empty is False:
    st.write('---')
    datashow = data[['city','address','event_day','start_event','setup_time','date_pick_up','hour_pick_up','principal_img']]
    formato = {'city':'Ciudad','address':'Dirección','event_day':'Fecha del evento','start_event':'Hora de evento','setup_time':'Hora de montaje','date_pick_up':'Fecha de recogida','hour_pick_up':'Hora de recogida'} 
    conteo  = 0
    for key,value in formato.items():
        if conteo % 2 == 0:
            col1, col2 = st.columns(2)
            with col1:
                st.text_input(f'{value}',value=datashow[key].iloc[0])
        else:
            with col2:
                st.text_input(f'{value}',value=datashow[key].iloc[0])           
        conteo += 1
    st.image(datashow['principal_img'].iloc[0],width=600)
