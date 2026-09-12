from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel

from app.db import get_database

ModelT = TypeVar("ModelT", bound=BaseModel)


class MongoRepository(Generic[ModelT]):
    """Thin CRUD wrapper mapping a Pydantic model straight to a Mongo
    collection, keyed by the model's own `<x>_id` field rather than Mongo's
    `_id`, so reads/writes never need translation."""

    def __init__(self, collection_name: str, model: Type[ModelT], id_field: str):
        self._collection_name = collection_name
        self._model = model
        self._id_field = id_field

    @property
    def _collection(self):
        return get_database()[self._collection_name]

    async def insert(self, item: ModelT) -> ModelT:
        doc = item.model_dump(mode="json")
        await self._collection.insert_one(doc)
        return item

    async def get(self, item_id: str) -> Optional[ModelT]:
        doc = await self._collection.find_one({self._id_field: item_id}, {"_id": 0})
        return self._model.model_validate(doc) if doc else None

    async def replace(self, item: ModelT) -> ModelT:
        doc = item.model_dump(mode="json")
        item_id = doc[self._id_field]
        await self._collection.replace_one({self._id_field: item_id}, doc, upsert=True)
        return item

    async def list(self, query: Optional[Dict[str, Any]] = None, sort_field: Optional[str] = None) -> List[ModelT]:
        cursor = self._collection.find(query or {}, {"_id": 0})
        if sort_field:
            cursor = cursor.sort(sort_field, -1)
        return [self._model.model_validate(doc) async for doc in cursor]
