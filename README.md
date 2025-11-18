# 🖥️ Marketing Assistant – AI Genesis Hackathon

An intelligent AI-powered Marketing Assistant built using a Retrieval-Augmented Generation (RAG) architecture on Qdrant.
Users provide key information about their business such as company name, product details, and target audience and the AI then generates tailored marketing content, leveraging stored knowledge and continuous user interaction.

# ⚙️ Architecture & Workflow
### 👨🏻‍💻 User Onboarding & Input Collection
Users sign up and enter marketing-related information including:
- Company/business name
- Product or service description
- Target audience
- Industry context
- Marketing goals

### 🚀 Intelligent Data Processing
An AI agent processes this metadata and extracts relevant business information.
This information is then embedded and stored in Qdrant as part of the RAG workflow.

### 💡 Smart Retrieval & Response Generation
When the user asks a question or requests marketing content:
- A second AI agent retrieves the most relevant stored information from Qdrant.
- The agent then generates tailored marketing responses, ensuring accuracy and personalization.

### 🗃️ Memory-Enhanced Interaction
The system uses conversational memory to maintain context over time, creating more natural and consistent interactions with the user.

# 🛠️ Technologies Used

- Qdrant – Vector database for embedding storage and retrieval
- PostgreSQL – Primary database for user accounts and metadata
- LangChain – Framework for building AI agents and orchestration
- FastAPI – Backend API and server-side logic
- Jinja2 + HTML/CSS/JS – Frontend UI for user interaction
  

  
