import streamlit as st
import pandas as pd
import re
import tempfile
import mysql.connector as sql
import boto3
import random
from datetime import datetime
from bs4 import BeautifulSoup
from sqlalchemy import create_engine 
from price_parser import Price

from pyhtml2pdf import converter

st.set_page_config(layout="wide")

user     = st.secrets["user"]
password = st.secrets["password"]
host     = st.secrets["host"]
schema   = st.secrets["schema"]

@st.cache(allow_output_mutation=True,ttl=600)
def data_clients():
    db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    data          = pd.read_sql("SELECT id,city,event_day,theme,contracted_package,client,celebrated_name,celebrated_name2,principal_img FROM partyplum.events" , con=db_connection)
    return data

#-----------------------------------------------------------------------------#
# Filtro

clients = data_clients()

clients.index = range(len(clients))
idd = clients.index>=0

if clients.empty is False:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        options = ['All']
        if sum(clients[idd]['city'].notnull())>0:
            opt     = sorted(clients[idd]['city'].unique())
            opt.remove('Bogota')
            opt     = ['Bogota']+opt
            options = options+opt
        ciudad = st.selectbox('Ciudad',options=options)
        if ciudad!='All':
            idd = (idd) & (clients['city']==ciudad)
            
    with col2:
        options = ['All']
        if sum(clients[idd]['client'].notnull())>0:
            options=options+sorted(clients[idd]['client'].unique())
        clientname = st.selectbox('Cliente',options=options)
        if clientname!='All':    
            idd = (idd) & (clients['client']==clientname)
        
    with col3:
        options = ['All']
        if sum(clients[idd]['celebrated_name'].notnull())>0:
            options=options+sorted(clients[idd]['celebrated_name'].unique())
        celebrated_name = st.selectbox('Nombre del festejado',options=options)
        if celebrated_name!='All':    
            idd = (idd) & (clients['celebrated_name']==celebrated_name)
            
    with col4:
        options = ['All']
        if sum(clients[idd]['celebrated_name2'].notnull())>0:
            options=options+sorted(clients[idd]['celebrated_name2'].unique())
        celebrated_name2 = st.selectbox('Nombre del festejado 2',options=options)
        if celebrated_name2!='All':    
            idd = (idd) & (clients['celebrated_name2']==celebrated_name2)
            
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        options = ['All']
        if sum(clients[idd]['contracted_package'].notnull())>0:
            options=options+sorted(clients[idd]['contracted_package'].unique())
        contracted_package = st.selectbox('Paquete contratado',options=options)
        if contracted_package!='All':    
            idd = (idd) & (clients['contracted_package']==contracted_package) 
            
    with col2:
        options = ['All']
        if sum(clients[idd]['theme'].notnull())>0:
            options=options+sorted(clients[idd]['theme'].unique())
        theme = st.selectbox('Tema',options=options)
        if theme!='All':    
            idd = (idd) & (clients['theme']==theme)
            
    with col3: 
        fechainicial = st.date_input('Fecha inicial',clients[idd]['event_day'].min())

    with col4:
        fechafinal = st.date_input('Fecha final',clients[idd]['event_day'].max())
       
clients.index = range(len(clients))
clients['event_day'] = pd.to_datetime(clients['event_day'],errors='coerce')
idd     = (clients['event_day']>=str(fechainicial)) & (clients['event_day']<=str(fechafinal))
clients = clients[idd]

#-----------------------------------------------------------------------------#

css_format = """
    <style>
      .event-card-left {
        width: 100%;
        height: 1200px;
        overflow-y: scroll; /* enable vertical scrolling for the images */
        text-align: justify;
        display: inline-block;
        margin: 0px auto;
      }

      .event-block {
        width:30%;
        background-color: white;
        border: 1px solid gray;
        box-shadow: 2px 2px 2px gray;
        padding: 3px;
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
        margin-left: 10px;
      }

      img{
        width:100%;
        height:200px;
        margin-bottom: 10px; 
      }
    </style>
"""
imagenes = ''
for i, inputval in clients.iterrows():
    imagen_principal =  "https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/sin_imagen.png"
    if isinstance(inputval['principal_img'], str) and len(inputval['principal_img'])>20: imagen_principal =  inputval['principal_img']
    else: imagen_principal = "https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/sin_imagen.png"
    id_event           = inputval['id']
    cliente            = inputval['client']
    celebrated_name    = inputval['celebrated_name']
    contracted_package =  inputval['contracted_package']
    theme              =  inputval['theme']
    dateevent          =  inputval['event_day']
    imagenes += f'''
          <div class="event-block">
            <a href="http://localhost:8501/Resumen_evento?id_event={id_event}" target="_blank">
            <div class="event-image">
              <img src="{imagen_principal}" alt="event image" onerror="this.src='https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/sin_imagen.png';">
            </div>
            </a>
            <p class="caracteristicas-info">Cliente: {cliente}</h3>
            <p class="caracteristicas-info">Festejado: {celebrated_name}</p>
            <p class="caracteristicas-info">Paquete: {contracted_package}</p>
            <p class="caracteristicas-info">Tema: {theme}</p>
            <p class="caracteristicas-info">Fecha: {dateevent}</p>
                    
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