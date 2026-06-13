import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import QtQuick3D
import QtQuick3D.Helpers
import "."

View3D {
    id: view3D
    anchors.fill: parent
    camera: cameraNode

    // Properties exposed for Python
    property alias trackedPosition: trackedNode.scenePosition
    property real effectorY: robot.endEffector.scenePosition.y
    property real effectorX: robot.endEffector.scenePosition.x
    property real effectorZ: robot.endEffector.scenePosition.z
    property real sceneEffectorX: effectorX - 100
    property real sceneEffectorY: effectorY - 90
    property real sceneEffectorZ: effectorZ
    property url boardTexture: "maps/boardTexture.png"
    property url floorTexture: "maps/floorTexture.png"
    property real x_offset: 100
    property alias bgColor: env.clearColor
    property alias bgMode: env.backgroundMode
    property alias floorColor: floorMaterial.baseColor
    property alias sphereOrangePos: sphereOrange.modelPosition
    property alias sphereOrangeRot: sphereOrange.modelRotationQuaternion
    property alias sphereGreenPos: sphereGreen.modelPosition
    property alias sphereGreenRot: sphereGreen.modelRotationQuaternion
    property alias sphereBluePos: sphereBlue.modelPosition
    property alias sphereBlueRot: sphereBlue.modelRotationQuaternion
    property alias spherePurplePos: spherePurple.modelPosition
    property alias spherePurpleRot: spherePurple.modelRotationQuaternion
    property alias sphereYellowPos: sphereYellow.modelPosition
    property alias sphereYellowRot: sphereYellow.modelRotationQuaternion
    property real sphereRadius: 20.0

    // Simulation settings
    property bool showShadows: true
    property bool showGrid: true
    property bool showAxes: false
    property bool showLabels: false
    property bool useAntialiasing: true

    environment: SceneEnvironment {
        id: env
        clearColor: "#191B20"
        backgroundMode: SceneEnvironment.Color
        antialiasingMode: view3D.useAntialiasing ? SceneEnvironment.MSAA : SceneEnvironment.NoAA
        antialiasingQuality: SceneEnvironment.High
        InfiniteGrid { 
            id: infiniteGrid
            visible: view3D.showGrid
            gridInterval: 10
        }
    }

    DirectionalLight {
        id: sceneLight
        eulerRotation.x: -35
        eulerRotation.y: -45
        castsShadow: view3D.showShadows
        shadowMapQuality: Light.ShadowMapQualityVeryHigh
        shadowFactor: 30
        brightness: 1
    }

    AxisHelper {
        visible: view3D.showAxes
        gridOpacity: 0.0
        scale: Qt.vector3d(0.3, 0.3, 0.3)
    }

    Model {
        id: cameraOrigin
        position.x: 150
        position.y: 300
        eulerRotation.y: 45
        eulerRotation.x: -20

        PerspectiveCamera {
            id: cameraNode
            clipNear: 1
            clipFar: 30000
            z: 1300
            fieldOfView: 30
        }
    }

    OrbitCameraController {
        camera: cameraNode
        origin: cameraOrigin
    }

    Openbotv_v1 {
        id: robot
        scale: Qt.vector3d(1000, 1000, 1000)
        position: Qt.vector3d(0, 90, 0)
        eulerRotation.y: 180
    }

    Box {
        id: box3D
        scale: Qt.vector3d(1000, 1000, 1000)
        eulerRotation.y: 0
        eulerRotation.z: 180
        position: Qt.vector3d(view3D.x_offset - 15, 105, -15)
    }

    Model {
        id: floor
        source: "meshes/floor.mesh"
        scale: Qt.vector3d(4000, 1, 4000)

        materials: [
            PrincipledMaterial {
                id: floorMaterial
                baseColor: "black"        // ← alias floorColor controla el color
                alphaMode: PrincipledMaterial.Blend
                opacityMap: Texture {
                    source: view3D.floorTexture   // solo actúa como máscara alpha
                }
                roughness: 0.5
                indexOfRefraction: 1.45
            }
        ]
        receivesShadows: true
    }

    Model {
        id: tablero
        
        // Define X by Y dimensions
        geometry: PlaneGeometry {
            plane: PlaneGeometry.XZ
            width: 369.57
            height: 159.766
        }
        scale: Qt.vector3d(1, 1, 1)
        position: Qt.vector3d(view3D.x_offset + 85, 100, 0)
        eulerRotation.y: 90

        materials: [
            PrincipledMaterial {
                baseColorMap: Texture {
                    generateMipmaps: true
                    mipFilter: Texture.Linear
                    magFilter: Texture.Linear
                    source: view3D.boardTexture
                }
                roughness: 0.5
                indexOfRefraction: 1.45
                cullMode: PrincipledMaterial.NoCulling
                alphaMode: PrincipledMaterial.Opaque
            }
        ]
        receivesShadows: true   
    }

    Sphere {
        id: sphereOrange
        sphereRadius: view3D.sphereRadius
        modelColor: "#d3612d"
        modelPosition: Qt.vector3d(0, 0, 0)
    }

    Sphere {
        id: sphereGreen
        sphereRadius: view3D.sphereRadius
        modelColor: "#44ff44"
        modelPosition: Qt.vector3d(0, 0, 0)
    }

    Sphere {
        id: sphereBlue
        sphereRadius: view3D.sphereRadius
        modelColor: "#4488ff"
        modelPosition: Qt.vector3d(0, 0, 0)
    }

    Sphere {
        id: sphereYellow
        sphereRadius: view3D.sphereRadius
        modelColor: "#c3f314"
        modelPosition: Qt.vector3d(0, 0, 0)
    }

    Sphere {
        id: spherePurple
        sphereRadius: view3D.sphereRadius
        modelColor: "#a11e90"
        modelPosition: Qt.vector3d(0, 0, 0)
    }

    // "Ghost" node that follows the object you want to track
    Node {
        id: trackedNode
        position: robot.endEffector ? robot.endEffector.scenePosition : Qt.vector3d(0, 0, 0)
    }

    // Overlay XYZ en esquina superior derecha
    Rectangle {
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: 10
        width: 160
        height: 80
        color: "#aa000000"
        radius: 6

        Column {
            anchors.centerIn: parent
            spacing: 4

            Label {
                color: "#ff4444"
                font.bold: true
                text: "X: " + sceneEffectorX.toFixed(4)
            }
            Label {
                color: "#4488ff"
                font.bold: true
                text: "Y: " + sceneEffectorZ.toFixed(4)
            }
            Label {
                color: "#44ff44"
                font.bold: true
                text: "Z: " + sceneEffectorY.toFixed(4)
            }
        }
    }

    Model {
        id: projectionCylinder

        source: "#Cylinder"

        position: Qt.vector3d(
            effectorX,
            effectorY / 2.0,   // center between Y=0 and endEffector.y
            effectorZ
        )

        scale: Qt.vector3d(
            0.04,                       // fine radius in X
            effectorY / 100,            
            0.04                        // fine radius in Z
        )

        materials: [
            PrincipledMaterial {
                baseColor: "#44ff44"
                roughness: 0.3
                metalness: 0.1
            }
        ]
    }

    Button {
        icon.source: "../icons/home.png"
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.margins: 10
        onClicked: {
            cameraOrigin.position = Qt.vector3d(150, 300, 0)
            cameraOrigin.eulerRotation = Qt.vector3d(-20, 45, 0)
            cameraNode.z = 1300
        }
    }

    // 1. FrameAnimation para forzar la actualización de coordenadas 2D en cada frame
    FrameAnimation {
        id: frameSync
        running: view3D.showLabels && view3D.visible
    }

    // 2. Repeater para etiquetas 2D (Layout: Texto Izquierda, Círculo Derecha)
    // Nota: Se mantiene en 2D por compatibilidad con la versión de Qt, 
    // pero simulamos profundidad mediante el valor de Z proyectado.
    Repeater {
        id: jointLabelsRepeater
        model: 6
        
        delegate: Item {
            id: labelDelegate
            
            // Resolución reactiva del nodo del robot
            property var jointNode: {
                if (!robot) return null;
                if (index === 0) return robot.joint1;
                if (index === 1) return robot.joint2;
                if (index === 2) return robot.joint3;
                if (index === 3) return robot.joint4;
                if (index === 4) return robot.joint5;
                if (index === 5) return robot.joint6;
                return null;
            }

            // Cálculo de posición 2D sincronizado con el render loop
            property vector3d pos2d: {
                let t = frameSync.elapsedTime;
                if (!view3D.showLabels || !jointNode) return Qt.vector3d(0,0,0);
                return view3D.mapFrom3DScene(jointNode.scenePosition);
            }

            // Visibilidad y Profundidad:
            // En 2D, los elementos siempre están "al frente" del 3D.
            // Para simular que está "detrás", reducimos la opacidad si el objeto está lejos.
            visible: view3D.showLabels && jointNode && pos2d.z > 0
            opacity: 1.0 // Ejemplo de atenuación por distancia
            
            x: pos2d.x - width + 12
            y: pos2d.y - height / 2
            width: labelRow.width
            height: labelRow.height
            z: 100 

            Row {
                id: labelRow
                spacing: 8
                layoutDirection: Qt.LeftToRight

                // 1. Etiqueta con el valor (A la izquierda)
                Rectangle {
                    width: angleText.width + 12
                    height: 28
                    radius: 5
                    color: "#220e0e8c"
                    border.color: "white"
                    border.width: 0.7
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        id: angleText
                        anchors.centerIn: parent
                        color: "white"
                        font.pixelSize: 11
                        font.bold: true
                        text: {
                            if (!jointNode) return "";
                            let rot = jointNode.eulerRotation;
                            let angle = Math.abs(rot.x) > 0.1 ? rot.x : (Math.abs(rot.y) > 0.1 ? rot.y : rot.z);
                            if (index === 1 || index === 2) angle = -angle;
                            return angle.toFixed(0) + "°";
                        }
                    }
                }

                // 2. Marcador circular (A la derecha, centrado en la articulación)
                Rectangle {
                    width: 24
                    height: 24
                    radius: 12
                    color: "transparent"
                    border.color: "white"
                    border.width: 2
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }
    }
}