import streamlit as st
import copy
import pandas as pd
import mysql.connector as sql
import time
from sqlalchemy import create_engine 
from datetime import datetime

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
def data_providers():
    db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    data          = pd.read_sql("SELECT * FROM partyplum.providers WHERE available=1" , con=db_connection)
    return data

@st.experimental_memo
def data_package():
    db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    data          = pd.read_sql("SELECT id_region, id as id_package ,package FROM partyplum.package" , con=db_connection)
    return data

@st.experimental_memo
def data_city():
    db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    data          = pd.read_sql("SELECT id_region,region, country FROM partyplum.city" , con=db_connection)
    return data


data_ciudad             = data_city() 
products                = data_products()
data_proveedores        = data_providers()
products_origen         = copy.deepcopy(products)
data_proveedores_origen = copy.deepcopy(data_proveedores)
variables_price_data    = list(products_origen)
products['cat_spn']     = products['category'].replace(['BASIC', 'BAKERY', 'ADDITIONAL'],['Básicos','Repostería','Adicionales'])
categoryspn             = {'Básicos':'BASIC','Repostería':'BAKERY','Adicionales':'ADDITIONAL'}


products          = products.sort_values(by=['cat_spn','item'],ascending=True)
products.index    = range(len(products))
idd               = products.index>=0
data_ciudad.index = range(len(data_ciudad))
iddcountry        = data_ciudad.index>=0

# Zona por defecto:
id_region_put = 1
region_put    = 'Bogota y alrededores'
 
col1,col2,col3,col4,col5 = st.columns(5)
with col1:
    pais       = st.selectbox('País',options=sorted(data_ciudad["country"].unique()))
    iddcountry = (iddcountry) & (data_ciudad['country']==pais)
        
with col2:
    options = ['All'] + sorted(data_ciudad[iddcountry]["region"].unique())
    region  = st.selectbox('Región',options=options)
    if region!='All':
        id_region  = data_ciudad[data_ciudad['region']==region]['id_region'].iloc[0]
        region_put = data_ciudad[data_ciudad['region']==region]['region'].iloc[0]
        idd     = (idd) & (products['id_region']==id_region)
        
with col3:
    tipocambio = st.selectbox('Cambiar o agregar',options=['Ninguno','Editar información de proveedores','Crear proveedores'])

if tipocambio=='Editar información de proveedores' and data_proveedores.empty is False:
    with col4:
        options = ['All'] + sorted(data_proveedores['name'].unique())
        nombre_proveedor = st.selectbox('Nombre del proveedor',options=options)
        if nombre_proveedor!='All':
            data_proveedores = data_proveedores[data_proveedores['name']==nombre_proveedor]
            
    with col5:
        options = ['All'] + sorted(products[idd]['cat_spn'].unique())
        tipocategoria = st.selectbox('Categoria',options=options)
        if tipocategoria!='All':
            idd = (idd) & (products['cat_spn']==tipocategoria)

products                      = products[idd]
products['available_product'] = copy.deepcopy(products['available'])
data_collapse_proveedores     = pd.DataFrame()

if data_proveedores.empty is False:
    data_proveedores['cat_spn'] = data_proveedores['category'].replace(['BASIC', 'BAKERY', 'ADDITIONAL'],['Básicos','Repostería','Adicionales'])
    data_collapse_proveedores   = data_proveedores.groupby('name').agg({'item': list,'contacto_name':'first','phone':'first','webpage':'first','category':list}).reset_index()

#-----------------------------------------------------------------------------#
# Crear proveedores
if tipocambio=='Crear proveedores':
    st.write('---')
    continuar  = True
    conteo     = 0
    dataexport = pd.DataFrame()
    for i in range(15):
        conteo += 1
        if continuar:
            continuar = False
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            with col1:
                name = st.text_input(f'Nombre del proveedor ({conteo})',value='')
            with col2:
                contacto = st.text_input(f'Nombre del contacto ({conteo})',value='')
            with col3:
                phone = st.text_input(f'Telefono del proveedor ({conteo})',value='')
            with col4:
                webpage = st.text_input(f'Pagina web ({conteo})',value='')
            with col5:
                region_put    = st.selectbox(f'Región donde opera ({conteo})',options=sorted(data_ciudad[iddcountry]["region"].unique()))
                id_region_put = data_ciudad[data_ciudad['region']==region_put]['id_region'].iloc[0]
            with col6:
                productos = st.multiselect(f'Productos ({conteo})',options=sorted(products['item'].unique()))
    
            datapaso = pd.DataFrame()
            if len(name)>=2 and productos is not None and len(productos)>0:
                continuar = True
                for j in productos:
                    categoria         = products[products['item']==j]['category'].iloc[0]
                    id_item = products[products['item']==j]['id_item'].iloc[0]
                    formatpaso = {'name':name.title().strip(),
                                 'contacto_name':contacto.title().strip(),
                                 'phone':phone,
                                 'webpage':webpage,
                                 'available':1,
                                 'id_region':id_region_put,
                                 'region':region_put,
                                 'id_item':id_item,
                                 'category':categoria,
                                 'date':datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                 'item':j
                                 }
                    datapaso = datapaso.append(pd.DataFrame([formatpaso]))
            dataexport = dataexport.append(datapaso)
            
    if dataexport.empty is False:
        if st.button('Guardar cambios'):
            with st.spinner("Guardando Datos"):
                
                # Guardar en la tabla de proveedores
                engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
                dataexport.to_sql('providers',engine,if_exists='append', index=False) 
                
                db_connection        = sql.connect(user=user, password=password, host=host, database=schema)
                data_proveedores_new = pd.read_sql("SELECT id,id_item,name FROM partyplum.providers WHERE available=1" , con=db_connection)

                if 'id' in dataexport: del dataexport['id']
                dataexport = dataexport.merge(data_proveedores_new,on=['id_item','name'],how='left',validate='1:1')
                
                # Guardar en la tabla de precios historica con el id
                engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
                dataexport.to_sql('providers_historic',engine,if_exists='append', index=False) 
                st.success('Datos guardados con exito')
                
                time.sleep(3)
                st.experimental_memo.clear()
                st.experimental_rerun()
                
#-----------------------------------------------------------------------------#
# Cambiar info proveedores

if tipocambio=='Editar información de proveedores':
    if data_collapse_proveedores.empty is False:
        st.write('---')
        conteo = 0
        datanewproduct = pd.DataFrame()
        data_collapse_proveedores['changeid']  = 0
        data_collapse_proveedores['available'] = 1
        data_collapse_proveedores['id_name']   = copy.deepcopy(data_collapse_proveedores['name'])
        data_collapse_proveedores.index        = range(len(data_collapse_proveedores))
        
        for i,items in data_collapse_proveedores.iterrows():
            conteo += 1
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            with col1:
                name  = st.text_input(f'Nombre del proveedor ({conteo})',value=items['name'])
                data_collapse_proveedores.loc[i,'name'] = name.title().strip()
                if name!=items['name']:
                    data_collapse_proveedores.loc[i,'changeid'] = 1
                   
            with col2:
                contacto = st.text_input(f'Nombre del contacto ({conteo})',value=items['contacto_name'])
                data_collapse_proveedores.loc[i,'contacto_name'] = contacto
                if contacto!=items['contacto_name']:
                    data_collapse_proveedores.loc[i,'changeid'] = 1
                    
            with col3:
                phone = st.text_input(f'Telefono del proveedor ({conteo})',value=items['phone'])
                data_collapse_proveedores.loc[i,'phone'] = phone
                if phone!=items['phone']:
                    data_collapse_proveedores.loc[i,'changeid'] = 1
                    
            with col4:
                webpage = st.text_input(f'Pagina web ({conteo})',value=items['webpage'])
                data_collapse_proveedores.loc[i,'webpage'] = webpage
                if webpage!=items['webpage']:
                    data_collapse_proveedores.loc[i,'changeid'] = 1
                
            with col5:
                options       = list(sorted(products['item'].unique()))
                default_items = [x for x in options if x in items['item']]
                productos     = st.multiselect(f'Productos ({conteo})', options=options, default=default_items)
                newproducts   = [x for x in productos if x not in items['item']]
            
            with col6:
                available_check = st.checkbox(f'Eliminar proveedor ({conteo})', value=False)
                available = 1
                if available_check:
                    available = 0
                    data_collapse_proveedores.loc[i,'available'] = 0
                    data_collapse_proveedores.loc[i,'changeid']  = 1
    
            if newproducts is not None and len(newproducts)>0:
                datapaso = pd.DataFrame()
                for j in newproducts:
                    categoria         = products[products['item']==j]['category'].iloc[0]
                    id_item = products[products['item']==j]['id_item'].iloc[0]
                    formatpaso = {'name':name.title(),
                                 'contacto_name':contacto.title().strip(),
                                 'phone':phone,
                                 'webpage':webpage,
                                 'available':available,
                                 'id_region':id_region_put,
                                 'region':region_put,
                                 'id_item':id_item,
                                 'category':categoria,
                                 'date':datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                 'item':j
                                 }
                    datapaso = datapaso.append(pd.DataFrame([formatpaso]))
                datanewproduct = datanewproduct.append(datapaso)
        data_collapse_proveedores = data_collapse_proveedores[data_collapse_proveedores['changeid']==1]
        
        # Guardar en la base de datos
        if data_collapse_proveedores.empty is False or datanewproduct.empty is False:
            if st.button('Guardar cambios'):
                with st.spinner("Guardando Datos"):
                    
                    # Reescribir cambios en la base e datos
                    if data_collapse_proveedores.empty is False:
                        
                        data_collapse_proveedores['date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        # Reemplazar datos en la base de datos de eventos
                        for i,items in data_collapse_proveedores.iterrows():
                            variables     = ['name','phone','webpage','date','available','id_name']
                            data2mysql    = pd.DataFrame([{'name':items['name'],'phone':items['phone'],'webpage':items['webpage'],'date':items['date'],'available':items['available'],'id_name':items['id_name']}])
                            valores       = list(data2mysql.apply(lambda x: tuple(x), axis=1).unique())
                            db_connection = sql.connect(user=user, password=password, host=host, database=schema)
                            cursor        = db_connection.cursor()
                            cursor.executemany(f"""UPDATE {schema}.providers SET name=%s,phone=%s,webpage=%s,date=%s,available=%s WHERE name=%s """,valores)
                            db_connection.commit()
                            db_connection.close()
                            
                        namelis              = 'name="'+'" OR name="'.join(sorted(data_collapse_proveedores['name'].to_list()))+'"'
                        db_connection        = sql.connect(user=user, password=password, host=host, database=schema)
                        data_proveedores_new = pd.read_sql(f"SELECT * FROM partyplum.providers WHERE {namelis}" , con=db_connection)
    
                        # Guardar en la tabla de precios historica
                        engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
                        data_proveedores_new.to_sql('providers_historic',engine,if_exists='append', index=False) 
                        
                    # Agregar proveeodres con nuevos productos
                    if datanewproduct.empty is False:
    
                        engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
                        datanewproduct.to_sql('providers',engine,if_exists='append', index=False) 
                        
                        db_connection        = sql.connect(user=user, password=password, host=host, database=schema)
                        data_proveedores_new = pd.read_sql("SELECT id,id_item,name FROM partyplum.providers WHERE available=1" , con=db_connection)
    
                        if 'id' in datanewproduct: del datanewproduct['id']
                        datanewproduct = datanewproduct.merge(data_proveedores_new,on=['id_item','name'],how='left',validate='1:1')
                        
                        # Guardar en la tabla de precios historica con el id
                        engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
                        datanewproduct.to_sql('providers_historic',engine,if_exists='append', index=False) 
                    
                    st.success('Datos guardados con exito')
                    
                    time.sleep(3)
                    st.experimental_memo.clear()
                    st.experimental_rerun()
    else: st.error('Aun no hay informacion de proveedores')