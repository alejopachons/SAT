import openai
import streamlit as st
import os
import requests
import pandas as pd
from datetime import datetime  # Importa datetime para obtener la fecha actual
import time
import uuid  # Para generar un session_id único

import json
from wordcloud import WordCloud, STOPWORDS
import matplotlib.pyplot as plt

# Ruta de la imagen de avatar
avatar_image = "img/iconoSofia.png"

# Set up the OpenAI client
openai.api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")

# Initialize assistant
assistant_id = st.secrets.get("ASSISTANT_ID")
openai_client = openai.Client(api_key=openai.api_key)
assistant = openai_client.beta.assistants.retrieve(assistant_id)

# Sidebar configuration for OpenAI API Key and Reportes
with st.sidebar:
    st.sidebar.image("img/logo.png", use_column_width=True)
    st.title('Sofía Chatbot')
    selected_tab = st.radio("Menú:", ["Sofía Chat", "Reportes"])

# Airtable configuration
airtable_api_key = st.secrets.get("AIRTABLE_API_KEY")  # Replace name when setting secrets
airtable_base_id = st.secrets.get("AIRTABLE_BASE_ID")  # Replace name when setting secrets
airtable_table_name = st.secrets.get("AIRTABLE_TABLE_NAME")  # Replace name when setting secrets

headers = {
    "Authorization": f"Bearer {airtable_api_key}",
    "Content-Type": "application/json"
}

# Generar un session_id único si no existe ya en session_state
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())  # Genera un UUID único para la sesión

# Obtener el session_id de la sesión actual
session_id = st.session_state.session_id

def enviar_mensaje_a_airtable(contenido, session_id):
    """Envía un mensaje de usuario a Airtable como un nuevo registro con la fecha actual."""
    url = f"https://api.airtable.com/v0/{airtable_base_id}/{airtable_table_name}"
    fecha_actual = datetime.now().strftime("%Y-%m-%d")  # Obtiene la fecha actual en formato YYYY-MM-DD
    payload = {
        "fields": {
            "Preguntas": contenido,       # Reemplaza "Preguntas" con el nombre de la columna en tu tabla
            "Fecha": fecha_actual,        # Reemplaza "Fecha" con el nombre de la columna de fecha en tu tabla
            "session_id": session_id      # Asegúrate de que el nombre del campo en Airtable sea "Session ID"
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    # if response.status_code == 200 or response.status_code == 201:
    #     st.success("Mensaje enviado a Airtable.")
    # else:
    #     st.error(f"Error al enviar el mensaje a Airtable: {response.status_code}")

# Airtable integration code (Reportes tab)
if selected_tab == "Reportes":
    st.subheader("Reportes")
    url = f"https://api.airtable.com/v0/{airtable_base_id}/{airtable_table_name}"
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        
        # Extrae los campos de los registros y conviértelos en un DataFrame
        records = [record['fields'] for record in data.get('records', [])]
        if records:
            df = pd.DataFrame(records)
            # Crear dos columnas para organizar las métricas lado a lado
            col1, col2 = st.columns([1, 1])

            col1.metric(label="Cantidad de sesiones", value=df['session_id'].nunique())
            col2.metric(label="Cantidad de preguntas", value=df.shape[0])

            st.dataframe(df[['Preguntas', 'Fecha']].sort_values(by=['Fecha'], ascending=False).reset_index(drop=True), use_container_width=True, hide_index=True, height=220)

            st.header("Sesiones y Preguntas por fecha", divider="gray")

            # Calcular la cantidad de preguntas y sesiones por fecha
            df_fecha_preguntas = df.groupby("Fecha").size().reset_index(name="Cantidad de Preguntas")
            df_fecha_sesiones = df.groupby("Fecha")['session_id'].nunique().reset_index(name="Cantidad de Sesiones")

            # Unir ambos DataFrames en uno solo
            df_combined = pd.merge(df_fecha_preguntas, df_fecha_sesiones, on="Fecha")

            # Graficar ambas métricas en un solo gráfico de líneas
            st.line_chart(df_combined.set_index("Fecha"))

            # Generar la nube de palabras
            st.header("Nube de Palabras de Preguntas", divider="gray")
            
            # Concatenar todas las preguntas en un solo texto
            texto = " ".join(df['Preguntas'].dropna())

            # Crear la nube de palabras
            stopwords = set(STOPWORDS)
            stopwords.update([
                "de", "la", "que", "el", "en", "y", "a", "los", "del", "se", "las", 
                "por", "un", "para", "con", "no", "una", "su", "al", "lo", "como", 
                "más", "pero", "sus", "le", "ya", "o", "este", "sí", "porque", 
                "esta", "entre", "cuando", "muy", "sin", "sobre", "también", "me",
                "hasta", "hay", "donde", "quien", "desde", "todo", "nos", "durante",
                "todos", "uno", "les", "ni", "contra", "otros", "ese", "eso", 
                "ante", "ellos", "e", "esto", "mí", "antes", "algunos", "qué",
                "unos", "yo", "otro", "otras", "otra", "él", "tanto", "esa", "estos",
                "mucho", "quienes", "nada", "muchos", "cual", "poco", "ella", "estar",
                "estas", "algunas", "algo", "nosotros", "mi", "mis", "tú", "te", "ti", 
                "tu", "tus", "ellas", "nosotras", "vosotros", "vosotras", "os", "mío", 
                "mía", "míos", "mías", "tuyo", "tuya", "tuyos", "tuyas", "suyo", 
                "suya", "suyos", "suyas", "nuestro", "nuestra", "nuestros", "nuestras",
                "vuestro", "vuestra", "vuestros", "vuestras", "es"
            ])
            wordcloud = WordCloud(width=800, height=400, background_color="white", stopwords=stopwords).generate(texto)

            # Mostrar la nube de palabras
            fig, ax = plt.subplots()
            ax.imshow(wordcloud, interpolation="bilinear")
            ax.axis("off")

            st.pyplot(fig)

            st.header("Top 5 Preguntas Más Frecuentes", divider="gray")
            
            # Botón para ver las preguntas
            if st.button("Ver preguntas"):

                # Enviar las preguntas a OpenAI para obtener el top 5
                preguntas = "\n".join(df['Preguntas'].dropna())

                # Crear el prompt para OpenAI
                prompt = f"Estas son las preguntas enviadas:\n\n{preguntas}\n\nPor favor, dame el top 5 de las preguntas más comunes basadas en su frecuencia y su respectiva frecuencia. el formato de respuesta debe ser pregunta||cantidad. no agregue lista numerada a las preguntas"

                completion = openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "Eres un asistente que analiza datos de preguntas."},
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0,  # Hacer la salida más determinista
                    top_p=0.1       # Restringir el espacio de respuesta a las opciones más probables

                )

                # Extraer el contenido de la respuesta
                content = completion.choices[0].message.content

                # Procesar cada línea para obtener pregunta y cantidad, separadas por '||'
                preguntas_data = []
                for line in content.split("\n"):
                    parts = line.split("||")
                    if len(parts) == 2:
                        pregunta = parts[0].strip()
                        cantidad = parts[1].strip()
                        preguntas_data.append({"Pregunta": pregunta, "Cantidad": cantidad})

                # Crear el DataFrame con dos columnas: Pregunta y Cantidad
                df_top_5 = pd.DataFrame(preguntas_data)

                # Mostrar el DataFrame en Streamlit
                st.dataframe(df_top_5.sort_values(by=['Cantidad'], ascending=False), use_container_width=True, hide_index=True)



        else:
            st.warning("No records found in Airtable.")
    else:
        st.error(f"Failed to retrieve data: {response.status_code}")

# Initialize message history with a welcoming message if not already set

if selected_tab == "Sofía Chat":
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hola! ¿cómo puedo ayudarte hoy?"}
        ]

    # Display the message history
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar=avatar_image):
            st.markdown(message["content"])

    # Handle user input
    if prompt := st.chat_input("¿En qué puedo ayudarte?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        
        with st.chat_message("user"):
            st.markdown(prompt)

        # Start interaction with the assistant
        with st.chat_message("assistant", avatar=avatar_image):
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

            # Enviar el mensaje a Airtable con el session_id único
            enviar_mensaje_a_airtable(prompt, session_id)

            # Show initial status and wait for completion
            with st.spinner("Assistant is generating a response..."):
                time.sleep(5)

                # Retrieve the completed run and display the response
                run = openai_client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
                full_response = openai_client.beta.threads.messages.list(thread_id=thread.id).data[0].content[0].text.value
                message_placeholder.markdown(full_response)
                
        
        # Add assistant's response to message history
        st.session_state.messages.append({"role": "assistant", "content": full_response})
