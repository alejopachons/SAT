import openai
import streamlit as st
import os
import time

# Set up the OpenAI client
openai.api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")

# Initialize assistant
assistant_id = "asst_fRS1bZADCW3RQjy02u6CfYGI"
openai_client = openai.Client(api_key=openai.api_key)
assistant = openai_client.beta.assistants.retrieve(assistant_id)

# Sidebar configuration for OpenAI API Key
with st.sidebar:
    st.title('🤖💬 Sofía Chatbot')
    if openai.api_key:
        st.success('API key is set!', icon='✅')
    else:
        openai.api_key = st.text_input('Enter OpenAI API token:', type='password')
        if openai.api_key.startswith('sk-') and len(openai.api_key) == 51:
            st.success('Ready to chat!', icon='👉')
        else:
            st.warning('Please enter valid credentials!', icon='⚠️')

# Initialize message history with a welcoming message if it's not already set
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hola! ¿cómo puedo ayudarte hoy?"}
    ]

# Display the message history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle user input
if prompt := st.chat_input("What's on your mind?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
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
            # Pause briefly to allow processing
            time.sleep(5)
            
            # Retrieve the completed run and display the response
            run = openai_client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            full_response = openai_client.beta.threads.messages.list(thread_id=thread.id).data[0].content[0].text.value
            message_placeholder.markdown(full_response)
        
    # Add assistant's response to message history
    st.session_state.messages.append({"role": "assistant", "content": full_response})
