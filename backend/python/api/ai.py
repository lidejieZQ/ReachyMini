#!/usr/bin/env python3
"""
AI服务API路由
提供AI推理功能的REST API接口
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import base64
import io
from PIL import Image
import numpy as np
import cv2

from services.ai_service import ai_service
from utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/ai", tags=["ai"])


# 请求模型
class ImageAnalysisRequest(BaseModel):
    """图像分析请求"""
    image_data: str = Field(..., description="Base64编码的图像数据")
    analysis_type: str = Field("scene", description="分析类型: objects, faces, poses, scene")
    confidence_threshold: Optional[float] = Field(0.5, ge=0.1, le=1.0, description="置信度阈值")


class BatchAnalysisRequest(BaseModel):
    """批量分析请求"""
    images: List[str] = Field(..., description="Base64编码的图像数据列表")
    analysis_type: str = Field("objects", description="分析类型")
    confidence_threshold: Optional[float] = Field(0.5, description="置信度阈值")


# 响应模型
class DetectionItem(BaseModel):
    """检测项目"""
    class_name: str
    confidence: float
    bbox: List[int]  # [x1, y1, x2, y2]
    center: List[int]  # [x, y]
    area: float


class FaceItem(BaseModel):
    """人脸项目"""
    bbox: List[int]
    confidence: float
    landmarks: List[List[int]]
    identity: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    emotion: Optional[str] = None


class PoseItem(BaseModel):
    """姿态项目"""
    bbox: List[int]
    confidence: float
    keypoints: List[List[float]]  # [[x, y, confidence], ...]


class ObjectDetectionResponse(BaseModel):
    """目标检测响应"""
    success: bool
    timestamp: str
    processing_time: float
    detections: List[DetectionItem]
    total_objects: int


class FaceDetectionResponse(BaseModel):
    """人脸检测响应"""
    success: bool
    timestamp: str
    processing_time: float
    faces: List[FaceItem]
    total_faces: int


class PoseEstimationResponse(BaseModel):
    """姿态估计响应"""
    success: bool
    timestamp: str
    processing_time: float
    poses: List[PoseItem]
    total_poses: int


class SceneAnalysisResponse(BaseModel):
    """场景分析响应"""
    success: bool
    timestamp: str
    processing_time: float
    objects: Dict[str, Any]
    faces: Dict[str, Any]
    poses: Dict[str, Any]
    scene_summary: Dict[str, Any]


class AIStatsResponse(BaseModel):
    """AI统计响应"""
    initialized: bool
    models_loaded: List[str]
    inference_stats: Dict[str, Any]
    model_configs: Dict[str, Any]


@router.get("/status", response_model=AIStatsResponse)
async def get_ai_status():
    """获取AI服务状态"""
    try:
        stats = ai_service.get_stats()
        
        return AIStatsResponse(
            initialized=stats["initialized"],
            models_loaded=stats["models_loaded"],
            inference_stats=stats["inference_stats"],
            model_configs=stats["model_configs"]
        )
        
    except Exception as e:
        logger.error(f"获取AI服务状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect/objects", response_model=ObjectDetectionResponse)
async def detect_objects(request: ImageAnalysisRequest):
    """目标检测"""
    try:
        start_time = datetime.now()
        
        # 执行目标检测
        detections = await ai_service.detect_objects(request.image_data)
        
        # 过滤低置信度结果
        filtered_detections = [
            det for det in detections 
            if det.confidence >= request.confidence_threshold
        ]
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # 转换为响应格式
        detection_items = [
            DetectionItem(
                class_name=det.class_name,
                confidence=det.confidence,
                bbox=list(det.bbox),
                center=list(det.center),
                area=det.area
            ) for det in filtered_detections
        ]
        
        return ObjectDetectionResponse(
            success=True,
            timestamp=datetime.now().isoformat(),
            processing_time=processing_time,
            detections=detection_items,
            total_objects=len(detection_items)
        )
        
    except Exception as e:
        logger.error(f"目标检测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect/faces", response_model=FaceDetectionResponse)
async def detect_faces(request: ImageAnalysisRequest):
    """人脸检测"""
    try:
        start_time = datetime.now()
        
        # 执行人脸检测
        faces = await ai_service.detect_faces(request.image_data)
        
        # 过滤低置信度结果
        filtered_faces = [
            face for face in faces 
            if face.confidence >= request.confidence_threshold
        ]
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # 转换为响应格式
        face_items = [
            FaceItem(
                bbox=list(face.bbox),
                confidence=face.confidence,
                landmarks=[list(point) for point in face.landmarks],
                identity=face.identity,
                age=face.age,
                gender=face.gender,
                emotion=face.emotion
            ) for face in filtered_faces
        ]
        
        return FaceDetectionResponse(
            success=True,
            timestamp=datetime.now().isoformat(),
            processing_time=processing_time,
            faces=face_items,
            total_faces=len(face_items)
        )
        
    except Exception as e:
        logger.error(f"人脸检测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect/poses", response_model=PoseEstimationResponse)
async def estimate_poses(request: ImageAnalysisRequest):
    """姿态估计"""
    try:
        start_time = datetime.now()
        
        # 执行姿态估计
        poses = await ai_service.estimate_pose(request.image_data)
        
        # 过滤低置信度结果
        filtered_poses = [
            pose for pose in poses 
            if pose.confidence >= request.confidence_threshold
        ]
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # 转换为响应格式
        pose_items = [
            PoseItem(
                bbox=list(pose.bbox),
                confidence=pose.confidence,
                keypoints=[list(kp) for kp in pose.keypoints]
            ) for pose in filtered_poses
        ]
        
        return PoseEstimationResponse(
            success=True,
            timestamp=datetime.now().isoformat(),
            processing_time=processing_time,
            poses=pose_items,
            total_poses=len(pose_items)
        )
        
    except Exception as e:
        logger.error(f"姿态估计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/scene", response_model=SceneAnalysisResponse)
async def analyze_scene(request: ImageAnalysisRequest):
    """场景分析"""
    try:
        start_time = datetime.now()
        
        # 执行场景分析
        analysis = await ai_service.analyze_scene(request.image_data)
        
        if "error" in analysis:
            raise HTTPException(status_code=500, detail=analysis["error"])
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return SceneAnalysisResponse(
            success=True,
            timestamp=analysis["timestamp"],
            processing_time=processing_time,
            objects=analysis["objects"],
            faces=analysis["faces"],
            poses=analysis["poses"],
            scene_summary=analysis["scene_summary"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"场景分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/analyze")
async def upload_and_analyze(
    file: UploadFile = File(...),
    analysis_type: str = Form("scene"),
    confidence_threshold: float = Form(0.5)
):
    """上传图片并分析"""
    try:
        # 验证文件类型
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="只支持图片文件")
        
        # 读取文件内容
        file_content = await file.read()
        
        # 转换为base64
        image_base64 = base64.b64encode(file_content).decode('utf-8')
        image_data = f"data:{file.content_type};base64,{image_base64}"
        
        # 根据分析类型调用相应的API
        if analysis_type == "objects":
            request = ImageAnalysisRequest(
                image_data=image_data,
                analysis_type=analysis_type,
                confidence_threshold=confidence_threshold
            )
            return await detect_objects(request)
        elif analysis_type == "faces":
            request = ImageAnalysisRequest(
                image_data=image_data,
                analysis_type=analysis_type,
                confidence_threshold=confidence_threshold
            )
            return await detect_faces(request)
        elif analysis_type == "poses":
            request = ImageAnalysisRequest(
                image_data=image_data,
                analysis_type=analysis_type,
                confidence_threshold=confidence_threshold
            )
            return await estimate_poses(request)
        elif analysis_type == "scene":
            request = ImageAnalysisRequest(
                image_data=image_data,
                analysis_type=analysis_type,
                confidence_threshold=confidence_threshold
            )
            return await analyze_scene(request)
        else:
            raise HTTPException(status_code=400, detail=f"不支持的分析类型: {analysis_type}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/analyze")
async def batch_analyze(request: BatchAnalysisRequest):
    """批量图像分析"""
    try:
        if len(request.images) > 10:
            raise HTTPException(status_code=400, detail="批量分析最多支持10张图片")
        
        start_time = datetime.now()
        results = []
        
        for i, image_data in enumerate(request.images):
            try:
                if request.analysis_type == "objects":
                    detections = await ai_service.detect_objects(image_data)
                    filtered_detections = [
                        det for det in detections 
                        if det.confidence >= request.confidence_threshold
                    ]
                    results.append({
                        "index": i,
                        "success": True,
                        "detections": len(filtered_detections),
                        "data": [{
                            "class": det.class_name,
                            "confidence": det.confidence,
                            "bbox": det.bbox
                        } for det in filtered_detections]
                    })
                elif request.analysis_type == "faces":
                    faces = await ai_service.detect_faces(image_data)
                    filtered_faces = [
                        face for face in faces 
                        if face.confidence >= request.confidence_threshold
                    ]
                    results.append({
                        "index": i,
                        "success": True,
                        "faces": len(filtered_faces),
                        "data": [{
                            "confidence": face.confidence,
                            "bbox": face.bbox,
                            "emotion": face.emotion
                        } for face in filtered_faces]
                    })
                else:
                    results.append({
                        "index": i,
                        "success": False,
                        "error": f"不支持的分析类型: {request.analysis_type}"
                    })
            except Exception as e:
                results.append({
                    "index": i,
                    "success": False,
                    "error": str(e)
                })
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return JSONResponse(content={
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "processing_time": processing_time,
            "total_images": len(request.images),
            "successful_analyses": len([r for r in results if r["success"]]),
            "results": results
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def get_available_models():
    """获取可用的AI模型信息"""
    try:
        models_info = {
            "object_detection": {
                "name": "YOLOv8",
                "description": "实时目标检测模型",
                "classes": 80,
                "input_size": [640, 640],
                "supported_formats": ["jpg", "png", "bmp"]
            },
            "face_detection": {
                "name": "RetinaFace",
                "description": "高精度人脸检测模型",
                "features": ["detection", "landmarks", "age", "gender", "emotion"],
                "input_size": [320, 320],
                "supported_formats": ["jpg", "png", "bmp"]
            },
            "pose_estimation": {
                "name": "OpenPose",
                "description": "人体姿态估计模型",
                "keypoints": 17,
                "input_size": [256, 256],
                "supported_formats": ["jpg", "png", "bmp"]
            }
        }
        
        return JSONResponse(content=models_info)
        
    except Exception as e:
        logger.error(f"获取模型信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def ai_health_check():
    """AI服务健康检查"""
    try:
        stats = ai_service.get_stats()
        
        health_status = {
            "status": "healthy" if stats["initialized"] else "not_initialized",
            "initialized": stats["initialized"],
            "models_loaded": len(stats["models_loaded"]),
            "total_inferences": stats["inference_stats"]["total_inferences"],
            "average_inference_time": stats["inference_stats"]["average_time"],
            "last_inference_time": stats["inference_stats"]["last_inference_time"],
            "checks": {
                "service_initialized": stats["initialized"],
                "models_available": len(stats["models_loaded"]) > 0,
                "performance_ok": stats["inference_stats"]["average_time"] < 1.0
            }
        }
        
        # 根据健康状态设置HTTP状态码
        status_code = 200 if all(health_status["checks"].values()) else 503
        
        return JSONResponse(content=health_status, status_code=status_code)
        
    except Exception as e:
        logger.error(f"AI服务健康检查失败: {e}")
        return JSONResponse(
            content={
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            },
            status_code=503
        )