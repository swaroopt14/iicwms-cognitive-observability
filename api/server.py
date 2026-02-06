"""
IICWMS API Server
FastAPI-based API layer for system interaction.

Exposes:
- /events - Event ingestion and retrieval
- /hypotheses - Agent hypotheses and opinions
- /insights - Synthesized insights from master agent
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

# Import internal modules
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from blackboard.evidence_store import get_evidence_store
from graph.neo4j_client import Neo4jClient
from agents.master_agent import MasterAgent

# Initialize FastAPI app
app = FastAPI(
    title="IICWMS API",
    description="Intelligent IT Compliance & Workflow Monitoring System API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
evidence_store = get_evidence_store()
neo4j_client = None  # Lazy initialization
master_agent = None


def get_neo4j_client():
    """Lazy initialization of Neo4j client."""
    global neo4j_client
    if neo4j_client is None:
        neo4j_client = Neo4jClient()
        try:
            neo4j_client.connect()
        except Exception as e:
            print(f"Warning: Could not connect to Neo4j: {e}")
    return neo4j_client


def get_master_agent():
    """Lazy initialization of Master Agent."""
    global master_agent
    if master_agent is None:
        master_agent = MasterAgent(
            neo4j_client=get_neo4j_client(),
            evidence_store=evidence_store
        )
    return master_agent


# ============================================
# Request/Response Models
# ============================================

class EventCreate(BaseModel):
    """Model for creating a new event."""
    event_type: str = Field(..., description="Type of the event")
    source: str = Field(..., description="Source system of the event")
    workflow_id: Optional[str] = Field(None, description="Associated workflow ID")
    step_id: Optional[str] = Field(None, description="Associated step ID")
    resource_id: Optional[str] = Field(None, description="Associated resource ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Event metadata")


class EventResponse(BaseModel):
    """Model for event response."""
    id: str
    timestamp: str
    event_type: str
    source: str
    workflow_id: Optional[str]
    step_id: Optional[str]
    resource_id: Optional[str]
    metadata: Dict[str, Any]


class EventBatch(BaseModel):
    """Model for batch event submission."""
    events: List[EventCreate]


class HypothesisResponse(BaseModel):
    """Model for hypothesis/opinion response."""
    id: str
    agent: str
    opinion_type: str
    confidence: float
    timestamp: str
    evidence: Dict[str, Any]
    explanation: str


class InsightResponse(BaseModel):
    """Model for insight response."""
    id: str
    timestamp: str
    category: str
    severity: str
    title: str
    summary: str
    confidence: float
    contributing_opinions: List[str]
    recommended_actions: List[str]
    explanation: str


class AnalyzeRequest(BaseModel):
    """Model for analysis request."""
    workflow_id: Optional[str] = None
    resource_id: Optional[str] = None
    event_ids: Optional[List[str]] = None


# ============================================
# Health & Status Endpoints
# ============================================

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "IICWMS API",
        "version": "1.0.0",
        "description": "Intelligent IT Compliance & Workflow Monitoring System",
        "endpoints": {
            "events": "/events",
            "hypotheses": "/hypotheses",
            "insights": "/insights",
            "docs": "/docs"
        }
    }


@app.get("/health", tags=["Health"])
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "api": "up",
            "evidence_store": "up",
            "neo4j": "up" if neo4j_client else "not_initialized"
        }
    }


# ============================================
# Events Endpoints
# ============================================

@app.post("/events", response_model=EventResponse, tags=["Events"])
async def create_event(event: EventCreate):
    """
    Create a new event.
    
    Events are the primary input to the system. Each event is recorded
    and can trigger agent analysis.
    """
    event_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    
    event_data = {
        "id": event_id,
        "timestamp": timestamp,
        "event_type": event.event_type,
        "source": event.source,
        "workflow_id": event.workflow_id,
        "step_id": event.step_id,
        "resource_id": event.resource_id,
        "metadata": event.metadata
    }
    
    # Store in Neo4j if connected
    try:
        client = get_neo4j_client()
        if client:
            client.record_event(event_data)
    except Exception as e:
        print(f"Warning: Could not record event to Neo4j: {e}")
    
    return event_data


@app.post("/events/batch", tags=["Events"])
async def create_events_batch(batch: EventBatch):
    """
    Create multiple events in a batch.
    
    Efficient for bulk event ingestion from simulators or external systems.
    """
    results = []
    for event in batch.events:
        result = await create_event(event)
        results.append(result)
    
    return {
        "created": len(results),
        "events": results
    }


@app.get("/events", tags=["Events"])
async def list_events(
    workflow_id: Optional[str] = Query(None, description="Filter by workflow ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    limit: int = Query(50, ge=1, le=500, description="Maximum events to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    List events with optional filters.
    """
    try:
        client = get_neo4j_client()
        
        query = """
        MATCH (e:Event)
        WHERE ($workflow_id IS NULL OR e.workflow_id = $workflow_id)
        AND ($event_type IS NULL OR e.event_type = $event_type)
        RETURN e
        ORDER BY e.timestamp DESC
        SKIP $offset
        LIMIT $limit
        """
        
        results = client.execute_query(query, {
            "workflow_id": workflow_id,
            "event_type": event_type,
            "offset": offset,
            "limit": limit
        })
        
        return {"events": results, "count": len(results)}
    
    except Exception as e:
        return {"events": [], "count": 0, "warning": str(e)}


# ============================================
# Hypotheses Endpoints
# ============================================

@app.get("/hypotheses", tags=["Hypotheses"])
async def list_hypotheses(
    agent: Optional[str] = Query(None, description="Filter by agent"),
    opinion_type: Optional[str] = Query(None, description="Filter by opinion type"),
    confidence_min: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence"),
    limit: int = Query(50, ge=1, le=500, description="Maximum records to return")
):
    """
    List agent hypotheses/opinions from the evidence store.
    
    These are the raw opinions produced by individual agents before
    synthesis by the master agent.
    """
    records = evidence_store.search(
        agent=agent,
        opinion_type=opinion_type,
        confidence_min=confidence_min
    )
    
    return {
        "hypotheses": records[:limit],
        "total": len(records)
    }


@app.get("/hypotheses/{hypothesis_id}", tags=["Hypotheses"])
async def get_hypothesis(hypothesis_id: str):
    """
    Get a specific hypothesis by ID.
    
    Includes full evidence chain for traceability.
    """
    record = evidence_store.get(hypothesis_id)
    
    if not record:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    
    return record


# ============================================
# Insights Endpoints
# ============================================

@app.post("/insights/analyze", tags=["Insights"])
async def analyze(request: AnalyzeRequest):
    """
    Trigger analysis and generate insights.
    
    This orchestrates all agents to analyze the current system state
    and produce synthesized insights.
    """
    try:
        agent = get_master_agent()
        
        # Build context from request
        context = {}
        if request.workflow_id:
            context["workflow_id"] = request.workflow_id
        if request.resource_id:
            context["resource_id"] = request.resource_id
        
        # Get events to analyze
        events = []
        if request.event_ids:
            client = get_neo4j_client()
            for event_id in request.event_ids:
                query = "MATCH (e:Event {id: $id}) RETURN e"
                result = client.execute_query(query, {"id": event_id})
                if result:
                    events.extend(result)
        
        # Run analysis
        insights = agent.analyze(events, context)
        
        return {
            "insights": [i.to_dict() for i in insights],
            "count": len(insights),
            "analyzed_events": len(events)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/insights", tags=["Insights"])
async def list_insights(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(20, ge=1, le=100, description="Maximum insights to return")
):
    """
    List recent insights.
    
    Insights are the final synthesized outputs from the master agent,
    combining opinions from all specialized agents.
    """
    # Get recent hypotheses and synthesize on-demand
    records = evidence_store.get_recent(count=limit * 5)
    
    # Filter by type if needed
    if severity or category:
        records = [
            r for r in records 
            if (not severity or r.get("severity") == severity)
            and (not category or r.get("category") == category)
        ]
    
    return {
        "insights": records[:limit],
        "count": len(records[:limit])
    }


@app.get("/insights/{insight_id}", tags=["Insights"])
async def get_insight(insight_id: str):
    """
    Get a specific insight with full evidence chain.
    
    This provides complete traceability from insight back to
    original events and intermediate agent opinions.
    """
    evidence = evidence_store.get_by_insight(insight_id)
    
    return {
        "insight_id": insight_id,
        "evidence": evidence
    }


# ============================================
# Statistics Endpoints
# ============================================

@app.get("/stats", tags=["Statistics"])
async def get_stats():
    """
    Get system statistics.
    
    Includes counts of events, opinions, and insights.
    """
    store_stats = evidence_store.get_stats()
    
    return {
        "evidence_store": store_stats,
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# Application Startup/Shutdown
# ============================================

@app.on_event("startup")
async def startup_event():
    """Initialize components on startup."""
    print("IICWMS API starting up...")
    print(f"Evidence store: {evidence_store.filepath}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    print("IICWMS API shutting down...")
    if neo4j_client:
        neo4j_client.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
