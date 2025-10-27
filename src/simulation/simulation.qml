import QtQuick
import QtQuick.Controls
import QtQuick3D
import QtQuick3D.Helpers

// Importa también el QML generado
import "."   // o la carpeta donde está Avocado.qml

View3D {
    id: view3D
    anchors.fill: parent

    environment: ExtendedSceneEnvironment {
        backgroundMode: SceneEnvironment.SkyBox
        lightProbe: Texture {
            textureData: ProceduralSkyTextureData{
                textureQuality: ProceduralSkyTextureData.SkyTextureQualityHigh
            }
        }

        InfiniteGrid {
            gridInterval: 0.01
        }

        // Opciones FXAA, SMAA, SSAA, ProgressiveAA
        //antialiasingMode: SceneEnvironment.SSAA
        //antialiasingQuality: SceneEnvironment.VeryHigh
        
        tonemapMode: SceneEnvironment.TonemapModeAces 
    }

    DirectionalLight {
        eulerRotation.x: -45
        eulerRotation.y: 45
    }
    

    Node {
        id: originNode
        position: Qt.vector3d(0, 0.25, 0)
        eulerRotation: Qt.vector3d(-20, -135, 0)
        PerspectiveCamera {
            id: cameraNode
            position: Qt.vector3d(0, 0, 0.6)
            clipFar: 10
            clipNear: 0.05
        }
    }
    OrbitCameraController {
        anchors.fill: parent
        origin: originNode
        camera: cameraNode
    }

    // Instancia directamente el QML generado
    Openbotv_v1 {
        scale: Qt.vector3d(1, 1, 1)
    }

    Button {
        icon.source: "../gui/icons/home.png"
        text: ""
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.margins: 10

        onClicked: {
            originNode.position = Qt.vector3d(0, 0.25, 0)
            originNode.eulerRotation = Qt.vector3d(-20, -135, 0)
            cameraNode.position = Qt.vector3d(0, 0, 0.6)
        }
    }
}   

