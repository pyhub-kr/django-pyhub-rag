# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

django-pyhub-rag is a Django library that enables easy RAG (Retrieval Augmented Generation) implementation in Django projects. It supports Windows/Mac/Linux and provides PDF parsing with image extraction, vector store integration, and multiple LLM provider support.

## Development Commands

### Common Development Tasks

```bash
# Run tests
make test

# Run specific test file
make test tests/test_llm.py

# Format code (auto-fix)
make format

# Check code formatting (no changes)
make lint

# Build package
make build

# Run documentation server locally
make docs

# Build documentation
make docs-build
```

### CLI Commands

```bash
# Parse PDF with Upstage API (extracts images and generates descriptions)
pyhub.parser upstage file.pdf

# LLM operations
pyhub.llm ask "your question"
pyhub.llm describe image.png
pyhub.llm embed "text to embed"
pyhub.llm chat  # Interactive chat session
pyhub.llm compare "question" --models gpt-4o-mini --models claude-3-haiku
pyhub.llm agent run "Calculate 25 * 4"  # Run React Agent
pyhub.llm agent list-tools  # List available tools

# RAG operations
pyhub.rag sqlite-vec create-table  # Create vector table
pyhub.rag sqlite-vec load-jsonl data.jsonl  # Load JSONL data

# Document management
pyhub.doku  # Document management commands

# Run web server
pyhub.web
```

## Development Notes

- 테스트 시에는 pytest가 아니라 make test 명령을 활용한다.

## Testing

### Running Tests

#### Command Line (Recommended)
```bash
# Run all tests
make test

# Run specific test file  
make test tests/test_llm.py

# Using pytest directly
python -m pytest tests/test_fields_core.py -v

# Skip vector database tests (when sqlite-vec not available)
SKIP_DATABASE_TESTS=1 python -m pytest tests/
```

#### PyCharm/IDE Setup
For PyCharm or other IDEs using Django's test runner, use the dedicated settings module:

**Settings → Languages & Frameworks → Django → Settings:**
- Django project root: `/path/to/django-pyhub-rag`
- Settings: `tests.django_settings`
- Manage script: `/path/to/django-pyhub-rag/tests/manage.py`

**Run Configuration:**
- Test: Django tests
- Settings: `tests.django_settings`
- Working directory: `/path/to/django-pyhub-rag`

This configuration excludes vector-related apps to avoid sqlite-vec dependencies in the test environment.

### Test Organization
- All tests are centralized in the `tests/` directory
- Core field tests: `tests/test_fields_core.py`
- LLM file utilities: `tests/test_llm_files.py`
- Cache functionality: `tests/test_caches.py`
- Vector database models: `tests/test_models.py` (requires vector extensions)

## Architecture

### Django Apps Structure

#### 1. **core** - Base Utilities
- **Purpose**: Provides base utilities and custom fields used across the project
- **Key Features**:
  - Custom model fields (`PDFFileField`, `PageNumbersField`)
  - Static file management (htmx, alpine.js, marked.js, etc.)
  - Base templates and error pages
  - Configuration file management command (`pyhub_toml`)

#### 2. **doku** - Document Management
- **Purpose**: Handles PDF document upload, parsing, vectorization, and search
- **Key Models**:
  - `Document`: Manages uploaded PDF documents
  - `DocumentParseJob`: Tracks document parsing jobs
  - `VectorDocument`: Stores vectorized document chunks
  - `VectorDocumentImage`: Stores extracted images with AI-generated descriptions
- **Workflow**:
  1. PDF upload → Document creation
  2. Automatic DocumentParseJob creation (Django Lifecycle)
  3. Document parsing via Upstage API
  4. Text/image extraction and VectorDocument creation
  5. Automatic embedding generation and storage

#### 3. **llm** - LLM Integration
- **Purpose**: Provides unified interface for various LLM providers
- **Supported Providers**:
  - OpenAI (GPT-3.5, GPT-4)
  - Anthropic (Claude)
  - Google (Gemini)
  - Ollama (local models)
  - Upstage (Solar)
- **Key Features**:
  - Unified API (`LLM.create()`)
  - Async/streaming response support
  - Structured responses (choices parameter with JSON Schema)
  - Multimodal support (image input)
  - Automatic caching mechanism
  - React Agent system with tool integration
  - Input validation for tools to reduce unnecessary API calls

#### 4. **parser** - Document Parsing
- **Purpose**: PDF document parsing and image extraction
- **Key Features**:
  - Upstage Document Parse API integration
  - Image/table extraction and description generation
  - Template-based prompt management
  - CLI command: `pyhub.parser upstage`
- **Parsing Results**:
  - Separated text, images, and tables
  - Page-by-page structured data
  - AI-generated image/table descriptions

#### 5. **rag** - Vector Store
- **Purpose**: Vector database abstraction and similarity search
- **Supported Databases**:
  - PostgreSQL (pgvector extension)
  - SQLite (sqlite-vec extension)
- **Key Features**:
  - DB-agnostic VectorField implementation
  - Cosine similarity-based search
  - Langchain-compatible interface
  - Automatic embedding generation
  - Async search support

#### 6. **ui** - UI Components
- **Purpose**: Provides reusable UI components
- **Key Components**:
  - Modal: Modal dialogs
  - Alert: Alert messages
  - Toast: Toast notifications
  - Button: Styled buttons
- **Tech Stack**:
  - HTMX: Server-driven interactions
  - Alpine.js: Client-side state management
  - Django Cotton: Component templates

#### 7. **web** - Main Application
- **Purpose**: Django project configuration and integration
- **Key Features**:
  - Django settings management
  - URL routing
  - Account management (accounts)
  - Web server execution (`pyhub.web`)
- **Special Features**:
  - `pyhub.make_settings()` helper for automatic configuration
  - Automatic app detection and registration

### Key Design Patterns

1. **Provider Pattern**: LLM and vector store backends use abstract base classes with provider-specific implementations
2. **Caching Strategy**: API responses are cached (default: filesystem) to reduce costs with provider-specific cache namespaces
3. **Template-based Prompts**: Prompts stored in `templates/prompts/` directories using Django template engine
4. **Django Integration**: Full integration with Django ORM, cache system, and command extensions
5. **Async-First Design**: All major API calls support async operations, compatible with Django 4.0+ async views
6. **Lifecycle Hooks**: django-lifecycle for model event handling, automatic task triggers (embedding generation, parsing initiation)
7. **Multi-database Support**: Django routers for model-specific DB assignment, separation of vector and regular data

### Database Support

- PostgreSQL with pgvector extension for production (HNSW index for optimized search)
- SQLite with sqlite-vec for development/testing
- Custom vector fields that adapt to the database backend automatically

### Key Workflows

#### PDF Document RAG Workflow

```
1. PDF Upload
   └─> Document model creation
   
2. Automatic Parsing
   └─> DocumentParseJob creation (AFTER_CREATE hook)
   └─> Upstage API call
   
3. Content Extraction
   ├─> Text extraction → VectorDocument creation
   └─> Image extraction → VectorDocumentImage creation
       └─> LLM image description generation
       
4. Vectorization
   └─> Text embedding generation (AFTER_CREATE hook)
   └─> Vector DB storage
   
5. Search
   └─> Query embedding generation
   └─> Similarity search
   └─> Related documents retrieval
```

#### LLM Conversation Flow

```
1. User Query
   └─> LLM.create(model="gpt-4o-mini")
   
2. Cache Check
   └─> Cache hit → Immediate return
   └─> Cache miss → API call
   
3. API Call
   └─> Provider-specific implementation
   └─> Streaming/sync response handling
   
4. Response Processing
   └─> Cache storage
   └─> Return to user
```

#### React Agent Workflow

```
1. User Query
   └─> create_react_agent(llm, tools)
   
2. Agent Execution Loop
   ├─> Thought: Reasoning about the task
   ├─> Action: Select appropriate tool
   ├─> Action Input: Prepare tool parameters
   └─> Observation: Execute tool and get result
   
3. Iteration
   └─> Repeat Thought/Action/Observation cycle
   └─> Until Final Answer is reached
   
4. Tool Validation
   ├─> Input validation before execution
   ├─> Security checks (e.g., no code injection)
   └─> Error handling with informative messages
```

## Configuration Management

### Configuration Priority
1. System environment variables
2. `~/.pyhub.env` file
3. `~/.pyhub.toml` file
4. Default values in code

### Example Configuration
```toml
# ~/.pyhub.toml

[env]
UPSTAGE_API_KEY = "your-api-key"
OPENAI_API_KEY = "your-api-key"
ANTHROPIC_API_KEY = "your-api-key"
GOOGLE_API_KEY = "your-api-key"
DATABASE_URL = "postgresql://user:pass@host/db"

[prompt_templates.describe_image]
system = "Custom system prompt"
user = "Custom user prompt"

[cache]
default_timeout = 2592000  # 30 days
max_entries = 5000
```

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_llm.py

# Run with coverage
pytest --cov=pyhub
```

## Environment Variables

Required for full functionality:
- `UPSTAGE_API_KEY`: Document parsing
- `OPENAI_API_KEY`: OpenAI LLM provider
- `ANTHROPIC_API_KEY`: Anthropic LLM provider
- `GOOGLE_API_KEY`: Google LLM provider
- `DATABASE_URL`: Database connection string

Optional:
- `TOML_PATH`: Path to custom pyhub.toml file
- `ENV_PATH`: Path to .env file

## Key Implementation Notes

1. **Vector Fields**: Use `pyhub.rag.fields.VectorField` which automatically selects the appropriate backend (PostgreSQL or SQLite)
2. **LLM Calls**: Always use the caching decorator `@pyhub.llm.decorators.cache_result` for API calls
3. **Document Parsing**: Images are extracted and described separately, stored in `VectorDocumentImage` model
4. **Migrations**: Vector extension creation is handled in `rag/migrations/0001_create_vector_extension.py`
5. **Settings**: Use `pyhub.make_settings()` helper for Django settings configuration
6. **Async Operations**: All major operations support async execution, use `await` for async methods
7. **Batch Processing**: Use bulk operations for embedding generation to optimize performance
8. **Cache Management**: Provider-specific caches are isolated, clear specific caches when needed

## Extending the Library

### Adding a New LLM Provider
1. Inherit from `BaseLLM` class
2. Implement required methods (`ask`, `ask_async`, `embed`, etc.)
3. Register the provider in the factory method

### Custom Parser Implementation
1. Implement the `BaseParser` interface
2. Add parsing logic
3. Add CLI command

### Creating Custom Tools for Agents
1. Inherit from `BaseTool` or `AsyncBaseTool`
2. Define `args_schema` using Pydantic for input validation
3. Implement `run()` or `arun()` method
4. Set appropriate `validation_level` (STRICT, MODERATE, LENIENT)
5. Add custom validators for security checks

Example:
```python
from pyhub.llm.agents import BaseTool, ValidationLevel
from pydantic import BaseModel, Field

class WebSearchInput(BaseModel):
    query: str = Field(..., description="Search query")
    max_results: int = Field(5, ge=1, le=10)

class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Search the web for information"
    args_schema = WebSearchInput
    validation_level = ValidationLevel.STRICT
    
    def run(self, query: str, max_results: int = 5) -> str:
        # Implement web search logic
        return f"Found {max_results} results for: {query}"
```

### Prompt Customization
1. Add templates to `templates/prompts/` directory
2. Override in `~/.pyhub.toml`
3. Can be changed dynamically at runtime

## Security Considerations

### API Key Management
- Use environment variables or `.env` files
- Never hardcode in source code
- Add config files to `.gitignore`

### Data Isolation
- User-specific data separation
- Django permission system integration
- Permission checks during vector search

### Cache Security
- Exclude sensitive data from caching
- User-specific cache key generation
- Configure cache expiration times

## Performance Optimization

### Vector Search Optimization
- Choose appropriate dimension count (1536 recommended)
- Use indexes (PostgreSQL HNSW)
- Batch embedding generation

### API Cost Reduction
- Utilize aggressive caching
- Use smaller models when appropriate
- Implement streaming for faster response times

### Async Processing
- Async parsing for large documents
- Concurrent API call handling
- Django Channels integration available
