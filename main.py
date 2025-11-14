from fastapi import FastAPI
from routers import programmes, modules, graph
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(programmes.router)
app.include_router(modules.router)
app.include_router(graph.router)
