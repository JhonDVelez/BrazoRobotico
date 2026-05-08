# Graph Report - .  (2026-05-08)

## Corpus Check
- Large corpus: 119 files · ~1,167,603 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder, or use --no-semantic to run AST-only.

## Summary
- 877 nodes · 1160 edges · 90 communities (41 shown, 49 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 106 edges (avg confidence: 0.67)
- Token cost: 3,850 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_GUI|GUI]]
- [[_COMMUNITY_Control Utils|Control Utils]]
- [[_COMMUNITY_Simulation|Simulation]]
- [[_COMMUNITY_GUI|GUI]]
- [[_COMMUNITY_Device|Device]]
- [[_COMMUNITY_GUI|GUI]]
- [[_COMMUNITY_Plotting|Plotting]]
- [[_COMMUNITY_Calibration|Calibration]]
- [[_COMMUNITY_Camera|Camera]]
- [[_COMMUNITY_Control Utils|Control Utils]]
- [[_COMMUNITY_GUI|GUI]]
- [[_COMMUNITY_Controller|Controller]]
- [[_COMMUNITY_Color|Color]]
- [[_COMMUNITY_Calibration|Calibration]]
- [[_COMMUNITY_Control Utils|Control Utils]]
- [[_COMMUNITY_Config|Config]]
- [[_COMMUNITY_Color|Color]]
- [[_COMMUNITY_Camera|Camera]]
- [[_COMMUNITY_Camera|Camera]]
- [[_COMMUNITY_Vision|Vision]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Signals|Signals]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_GUI|GUI]]
- [[_COMMUNITY_GUI|GUI]]
- [[_COMMUNITY_Calibration|Calibration]]
- [[_COMMUNITY_Vision|Vision]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Vision|Vision]]
- [[_COMMUNITY_Simulation|Simulation]]
- [[_COMMUNITY_Vision|Vision]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Device|Device]]
- [[_COMMUNITY_Camera|Camera]]
- [[_COMMUNITY_GUI|GUI]]
- [[_COMMUNITY_Control Utils|Control Utils]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Camera|Camera]]
- [[_COMMUNITY_Camera|Camera]]
- [[_COMMUNITY_Camera|Camera]]
- [[_COMMUNITY_Control Utils|Control Utils]]
- [[_COMMUNITY_Controller|Controller]]
- [[_COMMUNITY_Controller|Controller]]
- [[_COMMUNITY_Controller|Controller]]
- [[_COMMUNITY_Control Utils|Control Utils]]
- [[_COMMUNITY_Control Utils|Control Utils]]
- [[_COMMUNITY_Control Utils|Control Utils]]
- [[_COMMUNITY_Control Utils|Control Utils]]
- [[_COMMUNITY_Control Utils|Control Utils]]
- [[_COMMUNITY_Control Utils|Control Utils]]
- [[_COMMUNITY_GUI|GUI]]
- [[_COMMUNITY_GUI|GUI]]
- [[_COMMUNITY_GUI|GUI]]
- [[_COMMUNITY_GUI|GUI]]
- [[_COMMUNITY_GUI|GUI]]
- [[_COMMUNITY_GUI|GUI]]
- [[_COMMUNITY_GUI|GUI]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Simulation|Simulation]]
- [[_COMMUNITY_Simulation|Simulation]]
- [[_COMMUNITY_Simulation|Simulation]]
- [[_COMMUNITY_Simulation|Simulation]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Camera|Camera]]
- [[_COMMUNITY_Camera|Camera]]
- [[_COMMUNITY_Camera|Camera]]
- [[_COMMUNITY_Signals|Signals]]
- [[_COMMUNITY_Signals|Signals]]
- [[_COMMUNITY_Community 81|Community 81]]
- [[_COMMUNITY_Community 82|Community 82]]
- [[_COMMUNITY_Graph|Graph]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Control Utils|Control Utils]]
- [[_COMMUNITY_Control Utils|Control Utils]]
- [[_COMMUNITY_Control Utils|Control Utils]]
- [[_COMMUNITY_Control Utils|Control Utils]]
- [[_COMMUNITY_Control Utils|Control Utils]]

## God Nodes (most connected - your core abstractions)
1. `CameraInterface` - 30 edges
2. `upgradableGraph` - 27 edges
3. `MainMenuMixin` - 25 edges
4. `CameraWorker` - 22 edges
5. `GraphWorker` - 20 edges
6. `KinematicsWorker` - 20 edges
7. `SimInterface` - 17 edges
8. `ColorInterface` - 16 edges
9. `ColorWindow` - 16 edges
10. `GraphInterface` - 16 edges

## Surprising Connections (you probably didn't know these)
- `Services Icon` --semantically_similar_to--> `CameraSignalManager`  [INFERRED] [semantically similar]
  src/gui/icons/services.png → src/data/control_utils.py
- `Controller Documentation` --references--> `DataFlow controller class`  [EXTRACTED]
  docs/developer-guide/data/controller.md → src/data/controller.py
- `Pose Estimation` --estimates_position_of--> `Red Target Sphere`  [EXTRACTED]
  AGENTS.md → Codigos_test/plano_con_esfera.jpg
- `ChArUco Calibration Board` --represents--> `ChArUco Board (12x5 squares)`  [EXTRACTED]
  Codigos_test/plano_vacio.jpg → AGENTS.md
- `Control Utils Documentation` --references--> `control_utils module`  [EXTRACTED]
  docs/developer-guide/data/control_utils.md → src/data/control_utils.py

## Hyperedges (group relationships)
- **6-DOF Robot Arm** — dynamixel_motor_id_1, dynamixel_motor_id_2, dynamixel_motor_id_3, dynamixel_motor_id_4, dynamixel_motor_id_5, dynamixel_motor_id_6 [EXTRACTED 1.00]
- **Camera Processing Pipeline** — src_gui_camera_worker, src_vision_charuco_detection, src_vision_ellipse_detection, src_vision_pose_estimation [EXTRACTED 1.00]
- **Documentation Stack** — mkdocs, material_theme, mkdocstrings [EXTRACTED 1.00]
- **Signal Manager Classes** — control_utils_signalmanager, control_utils_simulationsignalmanager, control_utils_physicalsignalmanager, control_utils_camerasignalmanager [EXTRACTED 1.00]
- **DataFlow Domain Configuration** — controller_dataflow, controller_domains, controller_simulationsignalmanager, controller_physicalsignalmanager [EXTRACTED 1.00]

## Communities (90 total, 49 thin omitted)

### Community 0 - "GUI"
Cohesion: 0.05
Nodes (18): Modulo donde se gestiona la estructura y comportamiento de la cámara cuyas imáge, Ventana de calibración de colores HSV para detección de elipses., GraphWorker, KinematicsThread, Renderizado dirigido por eventos (event-driven) con coalescencia:    - Cuando, Agenda un render para la próxima vuelta del event loop si no hay uno ya., Ejecuta el render; si han pasado muy pocos ms lo pospone (FPS cap)., Ejecuta cd() fuera del hilo GUI.      maxsize=1 garantiza que siempre se proce (+10 more)

### Community 1 - "Control Utils"
Cohesion: 0.06
Nodes (30): CameraSignalManager, Domains, DrawViewSignalManager, FrameCounter, get_instance(), GlobalTimer, Modes, PhysicalSignalManager (+22 more)

### Community 2 - "Simulation"
Cohesion: 0.05
Nodes (30): ChArUco Calibration Board, ChArUco Board (12x5 squares), PyBullet Physics, Qt Quick3D, Red Target Sphere, Paquete donde se maneja la simulación en pybullet asi como el ambiente para el m, Inicializa la clase RobotArmPhysics definiendo variables e iniciando el env de p, Obtiene el id del robot del motor de físicas de pybullet (+22 more)

### Community 3 - "GUI"
Cohesion: 0.06
Nodes (20): En este modulo se define el menu que se integrara a la barra de titulo y como se, ImageUtilsMixin, Modulo donde se gestiona el comportamiento de los pixmap (imágenes) presentes en, Carga una imagen desde la raíz del proyecto y la establece como pixmap en el lab, Envía los frames procesados de la cámara al QLabel          Args:             pi, Método para establecer el pixmap del video en el label reescalado si es necesari, Alterna el estado de la captura de video., Maneja el evento de redimensionamiento del widget.          Args:             ev (+12 more)

### Community 4 - "Device"
Cohesion: 0.06
Nodes (26): ABC, CameraEventFilterLinux, DeviceMonitor, DummyDeviceMonitor, get_device_monitor(), LinuxDeviceMonitor, Módulo abstracto para monitoreo de dispositivos multiplataforma. Abstrae la dete, Detiene el monitoreo de dispositivos. (+18 more)

### Community 5 - "GUI"
Cohesion: 0.06
Nodes (17): GraphInterface, GraphInterface simplificado: ya no gestiona ningún timer. Cada GraphWorker agend, Estructura de la sección de gráficas.      Con el renderizado event-driven en Gr, Inicia la simulación con recursos ya precargados, Clase encargada del modelo 3d usando contenedor completamente precargado, Configura la imagen estática que se muestra cuando no hay simulación, Integra el contenedor completamente precargado en la interfaz, SimInterface (+9 more)

### Community 6 - "Plotting"
Cohesion: 0.09
Nodes (7): PlotCursor, Clase encargada de manejar el buffer circular y la visualización     tipo oscilo, Asegura que el rango X no exceda los límites permitidos sin deformar la escala., Cambia la escala X usando el motor interno de pyqtgraph., Cambia la escala Y usando el motor interno de pyqtgraph., TimeAxisItem, upgradableGraph

### Community 7 - "Calibration"
Cohesion: 0.08
Nodes (13): CalibrationMenuMixin, Mixin encargado de definir el menu para la ventana de calibración,          las, Define la estructura del menu y submenus basado en las acciones definidas., Crea la barra de estado y conecta la visualization del estado de conexión del pu, MainMenuMixin, Define la estructura del menu y submenus basado en las acciones definidas., Escanea el sistema en busca de puertos de comunicación serial y los expone como, Mixin encargado de definir el menu, las acciones que hará y su comportamiento co (+5 more)

### Community 8 - "Camera"
Cohesion: 0.09
Nodes (13): CameraInterface, Configura las conexiones de eventos, Manejo del widget de video que muestra las imágenes de la cámara en un label de, Alterna el dibujo de rejilla en el procesamiento de frames, Alterna el dibujo de rejilla en el procesamiento de frames, Slot para manejar el frame listo del worker thread.          Args:             f, Maneja errores del worker thread de video.          Args:             error_mess, Inicia la captura de video desde la cámara y configura el worker             thr (+5 more)

### Community 9 - "Control Utils"
Cohesion: 0.07
Nodes (17): SearchSignalManager, MainActionsMixin, Modulo donde se define el comportamiento de los botones presentes en la interfaz, Gestiona el comportamiento de las secciones de la interfaz frente a distintas ac, Inicializa la ventana de calibración y detiene la cámara de la interfaz principa, Inicializa la ventana de calibración de colores y detiene la cámara de la interf, Inicia o detiene la simulation en caso de ser la primera vez instancia la clase, Inicia la colección con el microcontrolador en el puerto de comunicación selecci (+9 more)

### Community 10 - "GUI"
Cohesion: 0.09
Nodes (13): KinematicsWidget, Slot que recibe una lista de seis valores y actualiza el estado            estát, Configura las conexiones de eventos, Actualiza los valores almacenados de los slider/spinBox (estan conectados), Slot para cambios de modo. No oculta widgets ya que están en MainInitMixin., Regresa a su estado original los valores de los slider/spinBox (estan conectados, Actualizar los sliders/spinboxes desde una lista de 6 valores.          Se esper, Configura la interfaz de usuario del widget de video (+5 more)

### Community 11 - "Controller"
Cohesion: 0.09
Nodes (13): deg_to_rad(), Obtiene los valores objetivos de los slider/spinBox y los convierte a radianes, DataFlow, Obtiene los datos provenientes de la interfaz para los ángulos objetivos definid, Obtiene los datos provenientes de la interfaz para los ángulos objetivos definid, Clase que actúa como controlador de datos entre la interfaz y la simulación o el, Solicita los datos objetivos de los motores, es decir, los ángulos a los que se, Solicita los datos objetivos de los motores, es decir, los ángulos a los que se (+5 more)

### Community 12 - "Color"
Cohesion: 0.09
Nodes (14): ColorInterface, Procesa cada frame recibido para actualizar máscara y resultado., Coordina cámara, procesamiento HSV y guardado para ColorWindow., Actualiza la máscara HSV y la imagen resultante., Convierte un frame BGR a pixmap y lo ajusta al QLabel., Limpia las vistas procesadas al apagar la cámara., Funcionalidad de calibración HSV para ColorWindow., Conecta las señales de la ventana con la funcionalidad HSV. (+6 more)

### Community 13 - "Calibration"
Cohesion: 0.12
Nodes (10): CameraInterface, CalibrationInterface, Activa la captura del siguiente frame con detección de corners., Detecta corners ChArUco en una imagen en escala de grises., Ejecuta la calibración y retorna los parámetros., Muestra un popup de mensaje simple., Muestra un popup con la matriz de calibración en formato visual con QLabels., Procesamiento de frames para calibración con detección visualización en vivo. (+2 more)

### Community 14 - "Control Utils"
Cohesion: 0.12
Nodes (18): CameraSignalManager, Domains (Enum), GlobalTimer, Modes (Enum), Modes.KINEMATIC, PhysicalSignalManager, _SignalManager, SimulationSignalManager (+10 more)

### Community 15 - "Config"
Cohesion: 0.18
Nodes (16): _compact_dumps(), get(), get_app_dir(), init_config(), load(), _merge_defaults(), Crea CONFIG_DIR y asegura la integridad de las llaves en los JSON., Lee un archivo de config; si no existe lo recrea con defaults. (+8 more)

### Community 16 - "Color"
Cohesion: 0.15
Nodes (10): CalibrationMenuMixin, ColorWindow, Ventana para calibración de colores HSV., Crea un QLabel preparado para mostrar imágenes escaladas., Configura las conexiones de eventos., Carga el tema actual desde la configuración., Maneja el cambio de tema desde el ThemeManager., Maneja el cierre de la ventana. (+2 more)

### Community 17 - "Camera"
Cohesion: 0.15
Nodes (6): CameraWorker, on_charuco_done(), on_ellipses_done(), Modulo donde se implementa el hilo de procesamiento para la captura y el procesa, Slot conectado a FrameCounter.process_frame_signal.          Ejecuta la detecció, Worker thread para manejar la captura y procesamiento de video.      Captura en

### Community 18 - "Camera"
Cohesion: 0.14
Nodes (8): CameraControl, El truco de la división: Esta es la forma más agresiva de "ignorar" una sombra., Clase que gestiona una cámara y sus operaciones básicas        Optimizada para u, Enciende la cámara con configuración optimizada, Apaga la cámara y libera recursos, Verifica si la cámara está activa, Captura un frame de la cámara (BGR). Devuelve None si no hay frame., Libera recursos de la cámara

### Community 19 - "Vision"
Cohesion: 0.17
Nodes (9): ChArUcoDetection, Clase separada para detección de tableros ChArUco.      El detector mantiene dat, Extrapola las esquinas externas usando la homografía calculada.          Args:, Retorna un set con las coordenadas (col, row) de los corners interiores, Inicializa el detector de tableros ChArUco., Genera TODOS los puntos de la grilla en coordenadas 3D del tablero,         incl, Unifica todos los corners en una grilla ordenada de (cols × rows) puntos., Convierte la malla de esquinas en coordenadas físicas en milímetros.          Ar (+1 more)

### Community 20 - "Community 20"
Cohesion: 0.15
Nodes (8): CompletePreloader, PreloadedContainer, Clase principal main donde se realiza la carga de datos necesarios en la splash, Renderizado inicial seguro para cachear recursos, Limpia solo los recursos temporales de precarga, Contenedor que encapsula la vista precargada y su window container, Crea un widget padre temporal para el proceso de precarga, Precarga QQuickView + WindowContainer + Renderizado

### Community 21 - "Signals"
Cohesion: 0.14
Nodes (16): Control Utils Documentation, control_utils module, Controller Documentation, controller module, DataFlow controller class, deg_to_rad function, Domains enumeration, GlobalTimer (+8 more)

### Community 22 - "Community 22"
Cohesion: 0.25
Nodes (11): CD(), dashboard_refresher(), enviar_y_esperar_veloz(), HRx(), HRz(), HTx(), HTz(), JacobianoAnalitico() (+3 more)

### Community 23 - "GUI"
Cohesion: 0.15
Nodes (8): MainTitleBarMixin, Este modulo Se encarga de la estructura y comportamiento de la barra de titulo d, Equilibra los anchos de los contenedores laterales, Barra de titulo personalizada basado qframelesswindow, Re-equilibrar en cada resize, Equilibra el ancho de los contenedores laterales, QLabel, TitleBarBase

### Community 24 - "GUI"
Cohesion: 0.18
Nodes (8): FramelessMainWindow, MainWindow, Actualiza la ventana principal cuando otra ventana cambia el tema., Configura las conexiones de eventos para los botones de la interfaz, Ventana principal de la interfaz la cual hereda todos los mixin los cuales solo, Gestiona el evento de cerrado presentando una ventana para verificar la salida, MainActionsMixin, MainInitMixin

### Community 25 - "Calibration"
Cohesion: 0.21
Nodes (4): CameraCalibrationWindow, Carga el tema actual desde la configuración., Maneja el cambio de tema desde el ThemeManager., Captura el frame actual si hay detección de corners.

### Community 26 - "Vision"
Cohesion: 0.21
Nodes (6): PoseEstimation, Constructor de la tarea., Desplaza las coordenadas para que el punto elegido actúe como el origen (0,0,0)., Función principal ejecutada por el QThreadPool., Intersecta el rayo del centro 2D de la esfera con el plano paralelo al         t, Convierte un pixel distorsionado en un rayo normalizado de cámara.

### Community 27 - "Community 27"
Cohesion: 0.38
Nodes (10): CD(), CI(), H_DH(), HRx(), HRz(), HTx(), HTz(), JacobianoAnalitico() (+2 more)

### Community 28 - "Community 28"
Cohesion: 0.18
Nodes (11): Dynamixel Motor 1 (Base), Dynamixel Motor 2 (Shoulder), Dynamixel Motor 3 (Elbow), Dynamixel Motor 4 (Gripper Orientation), Dynamixel Motor 5 (Gripper Extension), Dynamixel Motor 6 (Gripper Open/Close), GOAL_POSITION Register (0x30), MOVING Register (0x46) (+3 more)

### Community 29 - "Vision"
Cohesion: 0.29
Nodes (3): DetectionDrawer, Calcula la escala de fuente basada en ancho de celda medida en pixeles., Dibuja la red final obtenida luego de la extrapolación sobre la imagen de refere

### Community 30 - "Simulation"
Cohesion: 0.24
Nodes (10): Simulation Environment, textureData, textureData10, textureData15, textureData20, textureData25, textureData30, textureData35 (+2 more)

### Community 31 - "Vision"
Cohesion: 0.22
Nodes (3): QRunnable, EllipseDetection, Detecta la esfera más grande de cada color en el frame.          Callback:

### Community 32 - "Community 32"
Cohesion: 0.39
Nodes (8): Robot Arm Links (visual meshes), arm1_link_1, arm2_link_1, arm3_link_1, arm4_link_1, base_link, clamp2_link_1, clamp_arm_link_1

### Community 34 - "Device"
Cohesion: 0.33
Nodes (6): Device Monitor Abstraction, Linux Device Monitor, Platform Compatibility, pyudev (Linux Device Monitor), win32con (Windows), Windows Device Monitor

### Community 35 - "Camera"
Cohesion: 0.33
Nodes (6): Arm Controls Panel, Camera Viewport, Joint Sliders (1-6), 3D Scene Viewer, Simulation Controls, User Interface

### Community 37 - "Control Utils"
Cohesion: 0.5
Nodes (4): config_manager (module), DrawViewSignalManager, FrameCounter, SearchSignalManager

### Community 38 - "Community 38"
Cohesion: 0.67
Nodes (3): Material Theme, MkDocs Documentation, mkdocstrings Plugin

### Community 39 - "Camera"
Cohesion: 0.67
Nodes (3): DirectShow Camera Capture, Camera Control, V4L2 Camera Capture

### Community 40 - "Camera"
Cohesion: 0.67
Nodes (3): Camera On Icon, CameraSignalManager, Services Icon

## Knowledge Gaps
- **327 isolated node(s):** `Calibra definiendo la esquina sup. izq. como (0,0)mm.`, `Clase principal main donde se realiza la carga de datos necesarios en la splash`, `Contenedor que encapsula la vista precargada y su window container`, `Crea un widget padre temporal para el proceso de precarga`, `Precarga QQuickView + WindowContainer + Renderizado` (+322 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **49 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `CameraInterface` connect `Camera` to `GUI`, `GUI`, `GUI`, `Color`, `Camera`?**
  _High betweenness centrality (0.158) - this node is a cross-community bridge._
- **Why does `CameraWorker` connect `Camera` to `GUI`, `Control Utils`, `Camera`, `Camera`, `Vision`, `Vision`, `Vision`, `Vision`?**
  _High betweenness centrality (0.147) - this node is a cross-community bridge._
- **Why does `ColorWindow` connect `Color` to `GUI`, `Camera`, `Control Utils`, `Color`, `GUI`?**
  _High betweenness centrality (0.106) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `CameraInterface` (e.g. with `CameraWorker` and `ThemeManager`) actually correct?**
  _`CameraInterface` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `upgradableGraph` (e.g. with `KinematicsThread` and `GraphWorker`) actually correct?**
  _`upgradableGraph` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `MainMenuMixin` (e.g. with `CalibrationMenuMixin` and `RobotWorker`) actually correct?**
  _`MainMenuMixin` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `CameraWorker` (e.g. with `CameraInterface` and `ChArUcoDetection`) actually correct?**
  _`CameraWorker` has 8 INFERRED edges - model-reasoned connections that need verification._