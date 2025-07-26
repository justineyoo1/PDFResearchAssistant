"""
PDF Research Assistant - Main Streamlit Application.

This is the main entry point for the PDF Research Assistant web application.
It provides a user interface for uploading PDFs and asking questions about them.
"""

import streamlit as st
import os
from typing import Optional

# Configure page
st.set_page_config(
    page_title="PDF Research Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main application function."""
    
    # Header
    st.title("📚 PDF Research Assistant")
    st.markdown("*Ask questions about your PDF documents using AI*")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        
        # API Key input
        api_key = st.text_input(
            "OpenAI API Key", 
            type="password",
            help="Enter your OpenAI API key to enable AI features"
        )
        
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
            st.success("✅ API Key configured")
        else:
            st.warning("⚠️ Please enter your OpenAI API key")
        
        st.divider()
        
        # Settings
        st.subheader("Settings")
        chunk_size = st.slider("Chunk Size", 500, 2000, 1000)
        top_k = st.slider("Results to Retrieve", 1, 10, 5)
        
    # Main content area
    tab1, tab2, tab3 = st.tabs(["📄 Upload & Process", "❓ Ask Questions", "📊 Document Library"])
    
    with tab1:
        st.header("Upload PDF Documents")
        
        uploaded_files = st.file_uploader(
            "Choose PDF files",
            type="pdf",
            accept_multiple_files=True,
            help="Upload one or more PDF files to analyze"
        )
        
        if uploaded_files:
            st.subheader("Uploaded Files")
            for file in uploaded_files:
                with st.expander(f"📄 {file.name}"):
                    st.write(f"**File size:** {file.size:,} bytes")
                    
                    if st.button(f"Process {file.name}", key=f"process_{file.name}"):
                        if not api_key:
                            st.error("Please enter your OpenAI API key in the sidebar first.")
                        else:
                            with st.spinner(f"Processing {file.name}..."):
                                # TODO: Implement PDF processing
                                st.info("PDF processing will be implemented in the next phase.")
                                st.success(f"✅ {file.name} processed successfully!")
    
    with tab2:
        st.header("Ask Questions")
        
        if not api_key:
            st.warning("Please configure your OpenAI API key in the sidebar to ask questions.")
        else:
            # Document selection
            st.subheader("Select Documents")
            doc_options = ["All Documents", "Document 1", "Document 2"]  # TODO: Dynamic list
            selected_docs = st.multiselect(
                "Choose documents to search in:",
                doc_options,
                default=["All Documents"]
            )
            
            # Question input
            question = st.text_area(
                "What would you like to know about your documents?",
                placeholder="e.g., What are the main conclusions of this research paper?",
                height=100
            )
            
            if st.button("🔍 Ask Question", type="primary"):
                if question:
                    with st.spinner("Searching documents and generating answer..."):
                        # TODO: Implement question answering
                        st.info("Question answering will be implemented in the next phase.")
                        
                        # Placeholder response
                        st.subheader("Answer")
                        st.write("This is where the AI-generated answer will appear.")
                        
                        st.subheader("Sources")
                        st.write("Relevant document excerpts will be shown here.")
                else:
                    st.error("Please enter a question.")
    
    with tab3:
        st.header("Document Library")
        
        # TODO: Implement document library
        st.info("Document library will show all processed PDFs with metadata and management options.")
        
        # Placeholder content
        st.subheader("Processed Documents")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Documents", "0")
        with col2:
            st.metric("Total Pages", "0")
        with col3:
            st.metric("Storage Used", "0 MB")
    
    # Footer
    st.divider()
    st.markdown(
        """
        <div style='text-align: center; color: #666;'>
            Built with ❤️ using Streamlit, LangChain, and OpenAI
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main() 