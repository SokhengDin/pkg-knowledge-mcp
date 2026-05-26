---
package: langchain
version_tested: 0.3.x
ecosystem: python
source: https://python.langchain.com/docs/
updated: 2025-05-26
---

# LangChain 0.3 — What Claude Code Needs to Know

## Import Paths (0.3.x)

All core primitives live in `langchain_core`, not `langchain`:

```python
from langchain_core.runnables import RunnableSequence, RunnablePassthrough, RunnableLambda
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.tools import tool, BaseTool
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore
```

Model integrations are in separate packages:
```python
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS, Chroma  # community = less maintained
```

## What Broke from 0.1/0.2 -> 0.3

| Removed | Replacement |
|---|---|
| `LLMChain` | LCEL pipe syntax: `prompt \| llm \| parser` |
| `ConversationBufferMemory` | `RunnableWithMessageHistory` |
| `initialize_agent` | `create_react_agent` from `langgraph` |
| `AgentExecutor` (legacy) | LangGraph agents |
| `LangChain` class | direct chain composition |
| `from langchain.chat_models import ChatOpenAI` | `from langchain_openai import ChatOpenAI` |
| `from langchain.schema import HumanMessage` | `from langchain_core.messages import HumanMessage` |

## LCEL (LangChain Expression Language) — Current Idiom

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    ("human", "{input}"),
])
llm = ChatOpenAI(model="gpt-4o")
parser = StrOutputParser()

chain = prompt | llm | parser  # LCEL pipe composition

result = chain.invoke({"input": "Hello"})
result = await chain.ainvoke({"input": "Hello"})  # async

for chunk in chain.stream({"input": "Hello"}):  # streaming
    print(chunk, end="", flush=True)
```

## Tool Calling (0.3.x)

```python
from langchain_core.tools import tool

@tool
def search(query: str) -> str:
    """Search the web for information."""
    return f"Results for: {query}"

llm_with_tools = llm.bind_tools([search])

# Tool calling returns AIMessage with tool_calls
msg = llm_with_tools.invoke("Search for LangChain docs")
# msg.tool_calls = [{"name": "search", "args": {"query": "LangChain docs"}, "id": "..."}]
```

## Memory / Chat History (0.3.x)

```python
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

store: dict[str, ChatMessageHistory] = {}

def get_session_history(session_id: str) -> ChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

chain_with_history = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="history",
)

chain_with_history.invoke(
    {"input": "Hi"},
    config={"configurable": {"session_id": "user-123"}},
)
```

## RAG Pattern (0.3.x)

```python
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.runnables import RunnablePassthrough
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
docs = splitter.split_documents(raw_docs)

vectorstore = FAISS.from_documents(docs, OpenAIEmbeddings())
retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

rag_chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)
```

## Streaming Callbacks

```python
from langchain_core.callbacks import StreamingStdOutCallbackHandler

llm = ChatOpenAI(
    model="gpt-4o",
    streaming=True,
    callbacks=[StreamingStdOutCallbackHandler()],
)
```

## Key Gotchas

- Always use `ainvoke` / `astream` in async contexts — sync methods block the event loop
- `ChatOpenAI` requires `OPENAI_API_KEY` env var; `ChatAnthropic` requires `ANTHROPIC_API_KEY`
- `langchain_community` packages are less maintained; prefer `langchain_openai`, `langchain_anthropic` etc.
- `.batch()` runs multiple inputs in parallel; use for bulk processing
- Pydantic v2 is supported in 0.3.x — use `model_validator` not `validator`
