import streamlit as st

nombre_proveedor            = st.text_input('Nombre Proveedor')
telefono_proveedor          = st.text_input('Telefono Proveedor')
paginaweb_proveedor         = st.text_input('Pagina web Proveedor')
categorias_proovedor        = st.multiselect('Categorias Proveedor',options=['Aguas', 'Flores', 'Globos', 'Impresiones', 'Transporte'])

