import streamlit as st
import copy
import pandas as pd
import mysql.connector as sql
import time
from sqlalchemy import create_engine 
from datetime import datetime
from price_parser import Price

st.set_page_config(layout="wide")

user     = st.secrets["user"]
password = st.secrets["password"]
host     = st.secrets["host"]
schema   = st.secrets["schema"]

@st.experimental_memo
def data_products():
    db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    data          = pd.read_sql("SELECT * FROM partyplum.products_package WHERE  available=1" , con=db_connection)
    return data

@st.experimental_memo
def data_city():
    db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    data          = pd.read_sql("SELECT id_region,region, country FROM partyplum.city" , con=db_connection)
    return data

@st.experimental_memo
def data_package():
    db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    data          = pd.read_sql("SELECT id_region, id as id_package ,package FROM partyplum.package" , con=db_connection)
    return data


products            = data_products()
products_origen     = copy.deepcopy(products)
packages            = data_package()
variables_origen    = list(products_origen)
products.index      = range(len(products))
idd                 = products.index>=0
products['cat_spn'] = products['category'].replace(['BASIC', 'BAKERY', 'ADDITIONAL','PRINT'],['Básicos','Repostería','Adicionales','Impresiones'])
categoryspn         = {'Básicos':'BASIC','Repostería':'BAKERY','Adicionales':'ADDITIONAL','Impresiones':'PRINT'}
data_ciudad         = data_city() 
data_ciudad.index   = range(len(data_ciudad))
iddcountry          = data_ciudad.index>=0

col1,col2,col3,col4,col5,col6 = st.columns(6)
with col1:
    pais       = st.selectbox('País',options=sorted(data_ciudad["country"].unique()))
    iddcountry = (iddcountry) & (data_ciudad['country']==pais)
        
with col2:
    region  = st.selectbox('Región',options=sorted(data_ciudad[iddcountry]["region"].unique()))
    if region!='All':
        id_region = data_ciudad[data_ciudad['region']==region]['id_region'].iloc[0]
        idd     = (idd) & (products['id_region']==id_region)
        
with col3:
    tipocambio = st.selectbox('Cambiar o agregar',options=['Seleccionar','Editar info de items','Añadir items'])
    
if tipocambio=='Editar info de items':
    with col4:
        options = ['All'] + sorted(products[idd]['package'].unique())
        paquete = st.selectbox('Paquete',options=options)
        if paquete!='All':
            idd = (idd) & (products['package']==paquete)
    
    with col5:
        options  = ['All'] + sorted(products[idd]['cat_spn'].unique())
        categoria = st.selectbox('Categoria',options=options)
        if categoria!='All':
            idd = (idd) & (products['cat_spn']==categoria)
            
    with col6:
        options  = ['All'] + sorted(products[idd]['item'].unique())
        producto = st.selectbox('Item',options=options)
        if producto!='All':
            idd = (idd) & (products['item']==producto)
        
        
#-----------------------------------------------------------------------------#
# Añadir items
if tipocambio=='Añadir items':
    st.write('---')
    
    conteo    = 0
    continuar = True
    data2products_package = pd.DataFrame()
    data2product          = pd.DataFrame()
    for i in range(30):
        conteo += 1
        col1,col2,col3 = st.columns(3)
        if continuar:
            continuar = False
            with col1:
                product  = st.text_input(f'Nombre del producto ({conteo})',value='')
                iddp     = products['item'].apply(lambda x: x.lower().strip())==product.lower().strip()
                if sum(iddp)>0:
                    st.error('El item ya existe')
                else:
                    if product!='' and len(product)>3:
                        with col2:
                            paquetes = st.multiselect(f'A que paquetes estará asociado ({conteo})',options=sorted(packages['package'].unique()),default=sorted(packages['package'].unique()))
                        with col3:
                            categoria  = st.selectbox(f'A que categoria pertenece ({conteo})',options=sorted(products['cat_spn'].unique()))
                            for key,value in categoryspn.items():
                                if key==categoria:
                                    categoria = value
                        if product!='' and len(product)>3:
                            continuar = True
                            datapaso  = {
                                 'region':region,
                                 'id_region':id_region,
                                 'date':datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                 'product':product.title().strip(),
                                 'category':categoria
                                 }
                            datapaso     = pd.DataFrame([datapaso])
                            data2product = data2product.append(datapaso)
                            for j in paquetes:
                                datapaso['package']    = j
                                datapaso['id_package'] = packages[(packages['package']==j) & (packages['id_region']==id_region)]['id_package'].iloc[0]
                                data2products_package  = data2products_package.append(datapaso)

    if st.button('Guardar cambios'):
        with st.spinner("Guardando Datos"):
            if data2product.empty is False:
                # Guardar en la base de datos de productos
                engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
                data2product.to_sql('products',engine,if_exists='append', index=False)
                
                # Guardar en la base de datos de products_package
                consulta = 'product="'+'" OR product="'.join(sorted(data2product['product'].unique()))+'"'
                db_connection    = sql.connect(user=user, password=password, host=host, database=schema)
                data_product_new = pd.read_sql(f"SELECT id as id_item, product, id_region FROM partyplum.products WHERE {consulta}" , con=db_connection)
                
                if 'id' in data2products_package: del data2products_package['id']
                data2products_package = data2products_package.merge(data_product_new, on=['product','id_region'],how='left',validate='m:1')
                
                data2products_package.rename(columns={'product':'item'},inplace=True)
                data2products_package['amount_default']     = 0
                data2products_package['unit_value_default'] = 0
                data2products_package['available']          = 1
                engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
                data2products_package.to_sql('products_package',engine,if_exists='append', index=False)        
                            
                # Guardar en la base de datos de products_package_historic
                consulta = 'item="'+'" OR item="'.join(sorted(data2products_package['item'].unique()))+'"'
                db_connection    = sql.connect(user=user, password=password, host=host, database=schema)
                data_product_new = pd.read_sql(f"SELECT * FROM partyplum.products_package WHERE {consulta}" , con=db_connection)
                
                engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
                data_product_new.to_sql('products_package_historic',engine,if_exists='append', index=False)        
                         
                st.success('Datos guardados con exito')
                
                time.sleep(3)
                st.experimental_memo.clear()
                st.experimental_rerun()
         
#-----------------------------------------------------------------------------#
# Cambiar cantidades, precios y  disponibilidad
if tipocambio=='Editar info de items':
    products = products[idd]
    if products.empty is False:
        st.write('---')
        conteo               = 0
        products['changeid'] = 0
        for i,items in products.iterrows():
            id_codigo = items['id']
            conteo += 1
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                paquete  = st.text_input(f'Paquete ({conteo})',value=items['package'])
    
            with col2:
                prodcuto = st.text_input(f'Nombre del producto ({conteo})',value=items['item'])
                
            with col3: 
                value    = items['amount_default']
                cantidad = st.number_input(f'Cantidad por defecto ({conteo})',min_value=0,value=value)
                cantidad = int(cantidad)
                products.loc[i,'amount_default'] = cantidad
                if cantidad<value or cantidad>value:
                    products.loc[i,'changeid'] = 1
    
            with col4: 
                value           = items['unit_value_default']
                precio_unitario = st.text_input(f'Precio unitario ({conteo})',value=f'${value:,.0f}')
                precio_unitario = Price.fromstring(precio_unitario).amount_float
                products.loc[i,'unit_value_default'] = precio_unitario
                if precio_unitario<value or precio_unitario>value:
                    products.loc[i,'changeid'] = 1
                    
            with col5:
                available_check = st.checkbox(f'Eliminar producto ({conteo})', value=False)
                if available_check:
                    products.loc[i,'available'] = 0
                    products.loc[i,'changeid']  = 1
    
    products = products[products['changeid']==1]
    if products.empty is False:
        if st.button('Guardar cambios'):
            with st.spinner("Guardando Datos"):
                # Reemplazar datos en la base de datos de eventos
                idlist = []
                for i,items in products.iterrows():
                    idlist.append(items['id'])
                    products['date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    variables        = ['amount_default','unit_value_default','date','available','id']
                    data2mysql    = products[variables]
                    valores       = list(data2mysql.apply(lambda x: tuple(x), axis=1).unique())
                    db_connection = sql.connect(user=user, password=password, host=host, database=schema)
                    cursor        = db_connection.cursor()
                    cursor.executemany(f"""UPDATE {schema}.products_package SET amount_default=%s,unit_value_default=%s,date=%s,available=%s WHERE id=%s """,valores)
                    db_connection.commit()
                    db_connection.close()   
                
                if idlist!=[]:
                    idlist = 'id='+' or id='.join([str(x) for x in idlist])
                    
                    db_connection     = sql.connect(user=user, password=password, host=host, database=schema)
                    data_products_new = pd.read_sql(f"SELECT * FROM partyplum.products_package WHERE {idlist}" , con=db_connection)
                    
                    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
                    data_products_new.to_sql('products_package_historic',engine,if_exists='append', index=False)        
                    
                st.success('Datos guardados con exito')
                
                time.sleep(3)
                st.experimental_memo.clear()
                st.experimental_rerun()