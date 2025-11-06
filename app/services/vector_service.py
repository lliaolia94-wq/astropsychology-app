"""
Сервис для работы с векторной базой данных Qdrant
Обеспечивает создание эмбеддингов, сохранение и поиск векторов
"""
import os
import logging
from typing import List, Dict, Optional, Any
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class VectorService:
    """Сервис для работы с векторной БД Qdrant"""
    
    VECTOR_DIMENSION = 384  # Размерность векторов для sentence-transformers
    COLLECTION_NAME = "context_vectors"
    
    def __init__(self):
        """Инициализация сервиса (ленивая загрузка компонентов)"""
        # Настройки Qdrant из переменных окружения (сохраняем для ленивой инициализации)
        self.qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", 6333))
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY", None)
        
        # Ленивая инициализация: клиент и модель загружаются только при использовании
        self.client = None
        self.embedding_model = None
        self._client_initialized = False
        self._model_initialized = False
    
    def _ensure_client_initialized(self):
        """Обеспечивает инициализацию клиента Qdrant (ленивая загрузка)"""
        if self._client_initialized:
            return
        
        try:
            if self.qdrant_api_key:
                self.client = QdrantClient(
                    url=f"http://{self.qdrant_host}:{self.qdrant_port}",
                    api_key=self.qdrant_api_key,
                    timeout=5
                )
            else:
                self.client = QdrantClient(
                    host=self.qdrant_host,
                    port=self.qdrant_port,
                    timeout=5
                )
            # Проверка подключения
            self.client.get_collections()
            logger.info(f"✅ Qdrant клиент подключен: {self.qdrant_host}:{self.qdrant_port}")
            # Инициализация коллекции при первом подключении
            self._ensure_collection_exists()
            self._client_initialized = True
        except Exception as e:
            logger.warning(f"⚠️ Qdrant недоступен: {str(e)}. Векторный поиск будет отключен.")
            logger.warning("   Для запуска Qdrant: docker run -d -p 6333:6333 qdrant/qdrant")
            self.client = None
            self._client_initialized = True  # Помечаем как инициализированный, чтобы не повторять попытки
    
    def _ensure_model_loaded(self):
        """Обеспечивает загрузку модели эмбеддингов (ленивая загрузка)"""
        if self._model_initialized:
            return
        
        try:
            model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
            logger.info(f"Загрузка модели эмбеддингов: {model_name}... (это может занять время при первом запуске)")
            self.embedding_model = SentenceTransformer(model_name)
            logger.info(f"✅ Модель эмбеддингов загружена: {model_name}")
            self._model_initialized = True
        except ImportError:
            logger.warning("⚠️ Библиотека sentence-transformers не установлена. Векторизация недоступна.")
            logger.warning("   Установите: pip install sentence-transformers")
            self._model_initialized = True
        except Exception as e:
            logger.warning(f"⚠️ Ошибка загрузки модели эмбеддингов: {str(e)}")
            logger.warning("   Векторизация будет недоступна. Проверьте интернет-соединение и место на диске.")
            self._model_initialized = True
    
    def _ensure_collection_exists(self):
        """Создание коллекции если её нет"""
        if not self.client:
            logger.warning("Qdrant клиент не инициализирован, пропускаем создание коллекции")
            return
        
        try:
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.COLLECTION_NAME not in collection_names:
                self.client.create_collection(
                    collection_name=self.COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=self.VECTOR_DIMENSION,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✅ Коллекция {self.COLLECTION_NAME} создана")
            else:
                logger.info(f"✅ Коллекция {self.COLLECTION_NAME} уже существует")
        except Exception as e:
            logger.error(f"❌ Ошибка создания коллекции: {str(e)}")
    
    def create_embedding(self, text: str) -> Optional[List[float]]:
        """
        Создание векторного представления текста
        
        Args:
            text: Текст для векторизации
            
        Returns:
            Список чисел (вектор) или None при ошибке
        """
        if not text:
            return None
        
        # Загружаем модель при необходимости (ленивая загрузка)
        self._ensure_model_loaded()
        
        if not self.embedding_model:
            return None
        
        try:
            embedding = self.embedding_model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"❌ Ошибка создания эмбеддинга: {str(e)}")
            return None
    
    def save_vector(
        self,
        vector_id: str,
        text: str,
        payload: Dict[str, Any]
    ) -> bool:
        """
        Сохранение вектора в Qdrant
        
        Args:
            vector_id: Уникальный ID вектора (UUID)
            text: Текст для векторизации
            payload: Метаданные для сохранения
            
        Returns:
            True при успехе, False при ошибке
        """
        # Инициализируем клиент при необходимости (ленивая загрузка)
        self._ensure_client_initialized()
        
        if not self.client:
            logger.warning("Qdrant клиент не инициализирован")
            return False
        
        try:
            # Создаем эмбеддинг
            vector = self.create_embedding(text)
            if not vector:
                logger.error("Не удалось создать эмбеддинг")
                return False
            
            # Добавляем текст в payload для полноты
            payload_with_text = payload.copy()
            payload_with_text["text"] = text
            
            # Сохраняем в Qdrant
            self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=[
                    PointStruct(
                        id=vector_id,
                        vector=vector,
                        payload=payload_with_text
                    )
                ]
            )
            
            logger.info(f"✅ Вектор сохранен: {vector_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения вектора: {str(e)}")
            return False
    
    def search_similar(
        self,
        query_text: str,
        user_id: Optional[int] = None,
        session_id: Optional[int] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10,
        score_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Семантический поиск похожих записей
        
        Args:
            query_text: Текст запроса
            user_id: Фильтр по ID пользователя
            session_id: Фильтр по ID сессии
            tags: Фильтр по тегам
            limit: Максимальное количество результатов
            score_threshold: Минимальный порог релевантности (0-1)
            
        Returns:
            Список найденных записей с метаданными
        """
        # Инициализируем клиент при необходимости (ленивая загрузка)
        self._ensure_client_initialized()
        
        if not self.client:
            logger.warning("Qdrant клиент не инициализирован")
            return []
        
        try:
            # Создаем эмбеддинг запроса
            query_vector = self.create_embedding(query_text)
            if not query_vector:
                logger.error("Не удалось создать эмбеддинг для запроса")
                return []
            
            # Строим фильтры
            filters = []
            if user_id:
                filters.append(
                    FieldCondition(key="user_id", match=MatchValue(value=user_id))
                )
            if session_id:
                filters.append(
                    FieldCondition(key="session_id", match=MatchValue(value=session_id))
                )
            if tags:
                # Для тегов используем OR условие (любой из тегов)
                tag_filters = [
                    FieldCondition(key="tags", match=MatchValue(value=tag))
                    for tag in tags
                ]
                # TODO: Реализовать OR логику для тегов (пока используем первый тег)
                if tag_filters:
                    filters.append(tag_filters[0])
            
            search_filter = Filter(must=filters) if filters else None
            
            # Выполняем поиск
            search_results = self.client.search(
                collection_name=self.COLLECTION_NAME,
                query_vector=query_vector,
                query_filter=search_filter,
                limit=limit,
                score_threshold=score_threshold
            )
            
            # Форматируем результаты
            results = []
            for result in search_results:
                results.append({
                    "vector_id": result.id,
                    "score": result.score,
                    "payload": result.payload
                })
            
            logger.info(f"✅ Найдено {len(results)} похожих записей")
            return results
        except Exception as e:
            logger.error(f"❌ Ошибка поиска: {str(e)}")
            return []
    
    def delete_vector(self, vector_id: str) -> bool:
        """
        Удаление вектора из Qdrant
        
        Args:
            vector_id: ID вектора для удаления
            
        Returns:
            True при успехе, False при ошибке
        """
        # Инициализируем клиент при необходимости (ленивая загрузка)
        self._ensure_client_initialized()
        
        if not self.client:
            logger.warning("Qdrant клиент не инициализирован")
            return False
        
        try:
            self.client.delete(
                collection_name=self.COLLECTION_NAME,
                points_selector=[vector_id]
            )
            logger.info(f"✅ Вектор удален: {vector_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка удаления вектора: {str(e)}")
            return False
    
    def update_vector_payload(
        self,
        vector_id: str,
        payload: Dict[str, Any]
    ) -> bool:
        """
        Обновление метаданных вектора
        
        Args:
            vector_id: ID вектора
            payload: Новые метаданные
            
        Returns:
            True при успехе, False при ошибке
        """
        # Инициализируем клиент при необходимости (ленивая загрузка)
        self._ensure_client_initialized()
        
        if not self.client:
            logger.warning("Qdrant клиент не инициализирован")
            return False
        
        try:
            self.client.set_payload(
                collection_name=self.COLLECTION_NAME,
                payload=payload,
                points=[vector_id]
            )
            logger.info(f"✅ Метаданные вектора обновлены: {vector_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка обновления метаданных: {str(e)}")
            return False


# Глобальный экземпляр сервиса
vector_service = VectorService()

