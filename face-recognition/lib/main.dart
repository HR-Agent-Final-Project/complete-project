import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'screens/camera_screen.dart';

List<CameraDescription>? cameras;

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await dotenv.load(fileName: '.env');

  try {
    cameras = await availableCameras();
  } catch (e) {
    debugPrint('Error getting cameras: $e');
    cameras = [];
  }

  runApp(const MyApp());
}

Widget _neoBall(double size, Color color) {
  return Container(
    width: size,
    height: size,
    decoration: BoxDecoration(
      color: color,
      shape: BoxShape.circle,
      border: Border.all(color: Colors.black, width: 3),
      boxShadow: const [
        BoxShadow(color: Colors.black, offset: Offset(4, 4), blurRadius: 0),
      ],
    ),
  );
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    CameraDescription? frontCamera;
    String? errorMessage;

    if (cameras == null || cameras!.isEmpty) {
      errorMessage = 'No cameras found. Please allow camera access.';
    } else {
      try {
        frontCamera = cameras!.firstWhere(
          (camera) => camera.lensDirection == CameraLensDirection.front,
        );
      } catch (e) {
        frontCamera = cameras!.first;
      }
    }

    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'HR Attendance',
      theme: ThemeData(
        scaffoldBackgroundColor: const Color(0xFFFFFBF0),
        fontFamily: 'monospace',
        useMaterial3: false,
      ),
      home: frontCamera != null
          ? CameraScreen(camera: frontCamera)
          : Scaffold(
              backgroundColor: const Color(0xFFFFFBF0),
              appBar: PreferredSize(
                preferredSize: const Size.fromHeight(56),
                child: Container(
                  decoration: const BoxDecoration(
                    color: Color(0xFFFFEE32),
                    border: Border(bottom: BorderSide(color: Colors.black, width: 3)),
                  ),
                  child: SafeArea(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 20),
                      child: Row(
                        children: [
                          Container(
                            width: 32,
                            height: 32,
                            color: Colors.black,
                            child: const Icon(Icons.fingerprint, color: Color(0xFFFFEE32), size: 20),
                          ),
                          const SizedBox(width: 12),
                          const Text(
                            'HR ATTENDANCE',
                            style: TextStyle(
                              fontSize: 20,
                              fontWeight: FontWeight.w900,
                              color: Colors.black,
                              letterSpacing: 2,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
              body: Stack(
                children: [
                  // Decorative neo balls
                  Positioned(top: -30, right: -20, child: _neoBall(100, const Color(0xFFFFEE32))),
                  Positioned(top: 120, left: -35, child: _neoBall(70, const Color(0xFF4ECDC4))),
                  Positioned(bottom: 180, right: -25, child: _neoBall(60, const Color(0xFFFF6B6B))),
                  Positioned(bottom: -20, left: 40, child: _neoBall(80, const Color(0xFFFFEE32))),
                  Positioned(top: 280, right: 30, child: _neoBall(40, const Color(0xFF4ECDC4))),
                  Positioned(bottom: 80, right: 100, child: _neoBall(35, const Color(0xFFFF6B6B))),
                  Positioned(top: 60, left: 80, child: _neoBall(25, Colors.white)),
                  // Main content
                  Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Container(
                            width: 120,
                            height: 120,
                            decoration: BoxDecoration(
                              color: const Color(0xFFFFEE32),
                              border: Border.all(color: Colors.black, width: 3),
                              boxShadow: const [
                                BoxShadow(color: Colors.black, offset: Offset(5, 5), blurRadius: 0),
                              ],
                            ),
                            child: const Icon(Icons.camera_alt_outlined, size: 60, color: Colors.black),
                          ),
                          const SizedBox(height: 28),
                          Container(
                            padding: const EdgeInsets.all(20),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              border: Border.all(color: Colors.black, width: 3),
                              boxShadow: const [
                                BoxShadow(color: Colors.black, offset: Offset(5, 5), blurRadius: 0),
                              ],
                            ),
                            child: Text(
                              errorMessage ?? 'No camera available',
                              textAlign: TextAlign.center,
                              style: const TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.w700,
                                color: Colors.black,
                              ),
                            ),
                          ),
                          const SizedBox(height: 28),
                          GestureDetector(
                            onTap: () {},
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 14),
                              decoration: BoxDecoration(
                                color: const Color(0xFFFFEE32),
                                border: Border.all(color: Colors.black, width: 3),
                                boxShadow: const [
                                  BoxShadow(color: Colors.black, offset: Offset(4, 4), blurRadius: 0),
                                ],
                              ),
                              child: const Text(
                                'RELOAD',
                                style: TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.w900,
                                  color: Colors.black,
                                  letterSpacing: 1.5,
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
    );
  }
}
