"""
Helper service for saving negotiations to the database using ORM.
"""
from sqlalchemy.orm import Session
from app.models.negotiation import Negotiation, NegotiationStatus


def save_negotiation(
    db: Session, 
    load_data: dict, 
    draft: dict,
    trucker_id: int = None,
    usage: dict = None
) -> Negotiation:
    """
    Save a negotiation draft to the database using ORM.
    
    Args:
        db: SQLAlchemy Session
        load_data: Dict with 'id', 'origin', 'destination', 'price', 'type'
        draft: Dict with 'subject' and 'body' (from AIAgentService)
        trucker_id: Optional trucker profile ID for attribution
        usage: Optional dict with token usage stats
    
    Returns:
        Negotiation: The saved Negotiation object
    """
    new_deal = Negotiation(
        load_id=str(load_data.get('id', '')),
        origin=load_data.get('origin', ''),
        destination=load_data.get('destination', ''),
        original_rate=float(load_data.get('price', 0)),
        target_rate=float(load_data.get('price', 0)) + 250,  # Example aggressive target
        ai_draft_subject=draft.get('subject', ''),
        ai_draft_body=draft.get('body', draft.get('draft', '')),  # Fallback to full draft if no body
        status=NegotiationStatus.PENDING,
        trucker_id=trucker_id
    )
    
    db.add(new_deal)
    db.flush()  # Get the ID without committing
    
    # Add token usage if provided (these columns exist in DB but not in ORM model yet)
    if usage:
        # Use raw SQL to set token columns (they're not in the ORM model)
        from sqlalchemy import text
        db.execute(text("""
            UPDATE webwise.negotiations
            SET ai_prompt_tokens = :prompt,
                ai_completion_tokens = :completion,
                ai_total_tokens = :total
            WHERE id = :id
        """), {
            "id": new_deal.id,
            "prompt": usage.get("prompt_tokens", 0),
            "completion": usage.get("completion_tokens", 0),
            "total": usage.get("total_tokens", 0)
        })
    
    db.commit()
    db.refresh(new_deal)
    return new_deal
