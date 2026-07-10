# PROPOSED FIX (new file, not yet wired in anywhere): shared helper for the
# consistent error model. Pairs with the global exception handlers proposed
# in main.py and the ErrorDetail/ErrorResponse schemas proposed in
# schemas.py.
#
# Every existing `raise HTTPException(status_code=X, detail="some string")`
# keeps working unmodified once the handlers in main.py are activated --
# they wrap a bare string detail into {"error": {"code": "http_error",
# "message": "some string"}} automatically. `api_error()` below is only for
# call sites that want a stable, machine-checkable `code` (e.g.
# "ticket_not_found" instead of the generic fallback) -- migrating
# individual `raise HTTPException(...)` call sites to it can happen
# incrementally after this is activated, it isn't required all at once.
#
# from fastapi import HTTPException
#
#
# def api_error(status_code: int, code: str, message: str) -> HTTPException:
#     return HTTPException(status_code=status_code, detail={"error": {"code": code, "message": message}})
#
#
# # Example call-site migration (not required, illustrative):
# #   raise HTTPException(status_code=404, detail="Ticket not found")
# # becomes:
# #   raise api_error(404, "ticket_not_found", "Ticket not found")
