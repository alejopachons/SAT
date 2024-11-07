import openai
import streamlit as st
import os
import requests
import pandas as pd
from datetime import datetime  # Importa datetime para obtener la fecha actual
import time


# Set up the OpenAI client
openai.api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")

# Initialize assistant
assistant_id = st.secrets.get("ASSISTANT_ID")
openai_client = openai.Client(api_key=openai.api_key)
assistant = openai_client.beta.assistants.retrieve(assistant_id)

# Sidebar configuration for OpenAI API Key and Reportes
with st.sidebar:
    st.title('🤖💬 Sofía Chatbot')
    selected_tab = st.radio("Select an option:", ["Chat", "Reportes"])
    
    # if openai.api_key:
    #     st.success('OPENAI API key is set!', icon='✅')
    # else:
    #     openai.api_key = st.text_input('Enter OpenAI API token:', type='password')
    #     if openai.api_key.startswith('sk-') and len(openai.api_key) == 51:
    #         st.success('Ready to chat!', icon='👉')
    #     else:
    #         st.warning('Please enter valid credentials!', icon='⚠️')

# Airtable configuration
airtable_api_key = st.secrets.get("AIRTABLE_API_KEY")  # Replace name when setting secrets
airtable_base_id = st.secrets.get("AIRTABLE_BASE_ID")  # Replace name when setting secrets
airtable_table_name = st.secrets.get("AIRTABLE_TABLE_NAME")  # Replace name when setting secrets

headers = {
    "Authorization": f"Bearer {airtable_api_key}",
    "Content-Type": "application/json"
}

def enviar_mensaje_a_airtable(contenido):
    """Envía un mensaje de usuario a Airtable como un nuevo registro con la fecha actual."""
    url = f"https://api.airtable.com/v0/{airtable_base_id}/{airtable_table_name}"
    fecha_actual = datetime.now().strftime("%Y-%m-%d")  # Obtiene la fecha actual en formato YYYY-MM-DD
    payload = {
        "fields": {
            "Preguntas": contenido,  # Reemplaza "Pregunta" con el nombre de la columna en tu tabla
            "Fecha": fecha_actual   # Reemplaza "Fecha" con el nombre de la columna de fecha en tu tabla
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    # if response.status_code == 200 or response.status_code == 201:
    #     st.success("Mensaje enviado a Airtable.")
    # else:
    #     st.error(f"Error al enviar el mensaje a Airtable: {response.status_code}")

# Airtable integration code (Reportes tab)
if selected_tab == "Reportes":
    st.subheader("Airtable Reportes")
    url = f"https://api.airtable.com/v0/{airtable_base_id}/{airtable_table_name}"
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        
        # Extrae los campos de los registros y conviértelos en un DataFrame
        records = [record['fields'] for record in data.get('records', [])]
        if records:
            df = pd.DataFrame(records)
            st.write("Data from Airtable:")
            st.metric(label="Cantidad de preguntas", value=df.shape[0])
            st.dataframe(df.sort_values(by=['Fecha'], ascending=False).reset_index(drop=True), use_container_width=True)


            st.header("Preguntas por fecha", divider="gray")

            df_fecha = df.groupby("Fecha").size().reset_index(name="Cantidad de Preguntas")

            st.bar_chart(df_fecha, x="Fecha", y="Cantidad de Preguntas")

        else:
            st.warning("No records found in Airtable.")
    else:
        st.error(f"Failed to retrieve data: {response.status_code}")

# Initialize message history with a welcoming message if not already set
if selected_tab == "Chat":
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hola! ¿cómo puedo ayudarte hoy?"}
        ]

    # Display the message history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Handle user input
    if prompt := st.chat_input("¿En qué puedo ayudarte?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Enviar el mensaje a Airtable
        enviar_mensaje_a_airtable(prompt)
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Start interaction with the assistant
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            
            # Create thread and run with assistant
            thread = openai_client.beta.threads.create(
                messages=[{"role": m["role"], "content": m["content"]}
                          for m in st.session_state.messages]
            )
            run = openai_client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistant.id,
            )

            # Show initial status and wait for completion
            with st.spinner("Assistant is generating a response..."):
                time.sleep(5)

                # Retrieve the completed run and display the response
                run = openai_client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
                full_response = openai_client.beta.threads.messages.list(thread_id=thread.id).data[0].content[0].text.value
                message_placeholder.markdown(full_response)
        
        # Add assistant's response to message history
        st.session_state.messages.append({"role": "assistant", "content": full_response})
