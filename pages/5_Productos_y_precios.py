import streamlit as st
import copy
import pandas as pd
import mysql.connector as sql
from sqlalchemy import create_engine 
from datetime import datetime
from price_parser import Price



st.set_page_config(layout="wide")

user     ='admin'
password ='Aa12345678'
host     ='data-proyect.cbpqfqlu2upq.us-east-2.rds.amazonaws.com'
schema   ='partyplum'

#user     = st.secrets["user"]
#password = st.secrets["password"]
#host     = st.secrets["host"]
#schema   = st.secrets["schema"]

@st.cache(allow_output_mutation=True,ttl=600)
def data_products_price():
    db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    data_price    = pd.read_sql("SELECT * FROM partyplum.products_price WHERE available=1" , con=db_connection)
    data_products = pd.read_sql("SELECT * FROM partyplum.products_package WHERE available=1" , con=db_connection)
    return data_price,data_products

@st.cache(allow_output_mutation=True,ttl=600)
def data_city():
    db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    data          = pd.read_sql("SELECT id as id_city, ciudad FROM partyplum.city" , con=db_connection)
    return data

data_ciudad              = data_city() 
data_price,data_products = data_products_price()
data_price_origen        = copy.deepcopy(data_price)
variables_price_data     = list(data_price_origen)
data_price['cat_spn']    = data_price['category'].replace(['PAQUETES', 'BAKERY', 'ADDITIONAL'],['Paquetes','Repostería','Adicionales'])
data_price               = data_price.sort_values(by=['cat_spn','product'],ascending=True)
data_price.index         = range(len(data_price))
idd                      = data_price.index>=0
id_city                  = None

col1,col2,col3 = st.columns(3)
with col1:
    options = ['All'] + sorted(data_ciudad["ciudad"].unique())
    ciudad  = st.selectbox('Ciudad',options=options)
    if ciudad!='All':
        id_city = data_ciudad[data_ciudad['ciudad']==ciudad]['id_city'].iloc[0]
        idd     = (idd) & (data_price['id_city']==id_city)
        
with col2:
    tipocambio = st.selectbox('Cambiar o agregar',options=['Ninguno','Cambiar precios de productos','Añadir productos'])
with col3:
    options = ['All'] + sorted(data_price[idd]['cat_spn'].unique())
    tipocategoria = st.selectbox('Categoria',options=options)
    if tipocategoria!='All':
        idd = (idd) & (data_price['cat_spn']==tipocategoria)

data_price = data_price[idd]

#-----------------------------------------------------------------------------#
# Agregar productos

if tipocambio=='Añadir productos':
    st.write('---')
    if id_city is None: id_city = 1
    tradcutor_categoria = {'Paquetes':'PAQUETES','Repostería':'BAKERY','Adicionales':'ADDITIONAL'}
    continuar  = True
    conteo     = 0
    dataexport = pd.DataFrame()
    for i in range(15):
        conteo += 1
        if continuar:
            continuar = False
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                product = st.text_input(f'Nombre del producto ({conteo})',value='')
            with col2: 
                valueU = st.text_input(f'Precio unitario producto ({conteo})',value='$0') 
                valueU = Price.fromstring(valueU).amount_float
            with col3:
                currency = st.selectbox(f'Tipo de moneda ({conteo})',options=['COP'])
            with col4:
                tipocategoria = st.selectbox(f'Categoria ({conteo})',options=['Paquetes','Repostería','Adicionales'])
                
            if valueU>0 or len(product)>2:
                continuar = True
                categoria = None
                for key,value in tradcutor_categoria.items():
                    if key==tipocategoria:
                        categoria = copy.deepcopy(value)
                datapaso  = pd.DataFrame([{'id_city':id_city,'product':product.title(),'unit_value_default':valueU,'category':categoria,'currency':currency,'available':1}])
                datapaso['date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                dataexport = dataexport.append(datapaso)
                
    if dataexport.empty is False:
        if st.button('Guardar cambios'):
            with st.spinner("Guardando Datos"):
                # Guardar en la tabla de precios para generar el id
                engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
                dataexport.to_sql('products_price',engine,if_exists='append', index=False) 
                
                db_connection  = sql.connect(user=user, password=password, host=host, database=schema)
                data_price_new = pd.read_sql("SELECT id,product FROM partyplum.products_price WHERE available=1" , con=db_connection)
                data_package   = pd.read_sql("SELECT id as id_package, package FROM partyplum.package WHERE available=1" , con=db_connection)
                
                if 'id' in dataexport: del dataexport['id']
                dataexport = dataexport.merge(data_price_new,on=['product'],how='left',validate='1:1')
                
                # Guardar en la tabla de precios historica con el id
                engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
                dataexport.to_sql('products_price_historic',engine,if_exists='append', index=False) 
                
                # Guardar en la tabla de products_package
                data2products_package = pd.DataFrame()
                for i,items in data_package.iterrows():
                    dataexport['id_package'] = items['id_package']
                    dataexport['package']    = items['package']
                    data2products_package    = data2products_package.append(dataexport)
                
                data2products_package.rename(columns={'product':'product_price','id':'id_product_price'},inplace=True)
                data2products_package['amount_default'] = 0
                
                idd = data2products_package['category'].isin(['PAQUETES','BAKERY'])
                if sum(idd)>0:
                    data2products_package = data2products_package[idd]
                    varkeep               = [x for x in list(data2products_package) if x in list(data_products)]
                    data2products_package = data2products_package[varkeep]
                    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
                    data2products_package.to_sql('products_package',engine,if_exists='append', index=False) 
                    
                    # Guardar en la tabla de products_package_historic
                    db_connection     = sql.connect(user=user, password=password, host=host, database=schema)
                    data_products_new = pd.read_sql("SELECT id,id_product_price,id_package FROM partyplum.products_package" , con=db_connection)
                    
                    if 'id' in data2products_package: del data2products_package['id']
                    data2products_package = data2products_package.merge(data_products_new,on=['id_product_price','id_package'],how='left',validate='1:1')
                    
                    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
                    data2products_package.to_sql('products_package_historic',engine,if_exists='append', index=False) 

                st.success('Datos guardados con exito')

#-----------------------------------------------------------------------------#
# Cambiar precios

if tipocambio=='Cambiar precios de productos':
    st.write('---')
    id_change_price     = []
    id_change_available = []
    conteo = 0
    for i,items in data_price.iterrows():
        conteo += 1
        id_codigo = items['id']
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            producto  = st.text_input(f'Concepto ({conteo})',value=items['product'])
            
        with col2:
            categoria = st.text_input(f'Categoria ({conteo})',value=items['cat_spn'])
                
        with col3:
            value    = items['unit_value_default']
            if value is None: value = 0 
            valorU   = st.text_input(f'Valor unitario ({conteo})',value=f"${value:,.0f}")
            valorU   = Price.fromstring(valorU).amount_float
            data_price.loc[i,'unit_value_default'] = valorU
            if valorU<value or valorU>value:
                id_change_price.append(id_codigo)
                
        with col4:
            moneda  = st.text_input(f'Tipo moneda ({conteo})',value=items['currency'])
     
        with col5:
            available_check = st.checkbox(f'Eliminar producto ({conteo})', value=False)
            if available_check:
                data_price.loc[i,'available'] = 0
                id_change_available.append(id_codigo)
            

    if id_change_price!=[] or id_change_available!=[]:
        if st.button('Guardar cambios'):
            with st.spinner("Guardando Datos"):
                # reemplazar en la data precios
                idd = (data_price['id'].isin(id_change_price)) | (data_price['id'].isin(id_change_available))
                if sum(idd)>0:
                    dataexport         = data_price[idd]
                    varkeep            = [x for x in variables_price_data if x in dataexport]
                    dataexport         = dataexport[varkeep]
                    if 'cat_spn' in dataexport : del dataexport['cat_spn']
                    dataexport['date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
                    dataexport.to_sql('products_price_historic',engine,if_exists='append', index=False)        
                    
                    # Reemplazar datos en la base de datos de eventos
                    for i,items in dataexport.iterrows():
                        variables     = ['unit_value_default','date','available','id']
                        data2mysql    = pd.DataFrame([{'unit_value_default':items['unit_value_default'],'date':items['date'],'available':items['available'],'id':items['id']}])
                        valores       = list(data2mysql.apply(lambda x: tuple(x), axis=1).unique())
                        db_connection = sql.connect(user=user, password=password, host=host, database=schema)
                        cursor        = db_connection.cursor()
                        cursor.executemany(f"""UPDATE {schema}.products_price SET unit_value_default=%s,date=%s,available=%s WHERE id=%s """,valores)
                        db_connection.commit()
                        db_connection.close()
                        
                # reemplazar en la data productos
                if id_change_available!=[]:
                    idd = data_products['id_product_price'].isin(id_change_available)
                    if sum(idd)>0:
                        dataexport = data_products[idd]
                        dataexport['available'] = 0
                        dataexport['date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
                        dataexport.to_sql('products_package_historic',engine,if_exists='append', index=False)                     
                        
                        # Reemplazar datos en la base de datos de eventos
                        dataexport = dataexport.drop_duplicates(subset='id_product_price',keep='first')
                        for i,items in dataexport.iterrows():
                            variables     = ['date','available','id_product_price']
                            data2mysql    = pd.DataFrame([{'date':items['date'],'available':items['available'],'id_product_price':items['id_product_price']}])
                            valores       = list(data2mysql.apply(lambda x: tuple(x), axis=1).unique())
                            db_connection = sql.connect(user=user, password=password, host=host, database=schema)
                            cursor        = db_connection.cursor()
                            cursor.executemany(f"""UPDATE {schema}.products_package SET date=%s,available=%s WHERE id_product_price=%s """,valores)
                            db_connection.commit()
                            db_connection.close()
                    
                st.success('Datos guardados con exito')