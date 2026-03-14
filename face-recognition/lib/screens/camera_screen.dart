import 'dart:convert';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:path/path.dart' show join;
import 'package:path_provider/path_provider.dart';
import 'package:http/http.dart' as http;
import 'package:geolocator/geolocator.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

// ─── Neobrutalism design tokens ────────────────────────────────────────────
const _kYellow = Color(0xFFFFEE32);
const _kTeal = Color(0xFF4ECDC4);
const _kCoral = Color(0xFFFF6B6B);
const _kCream = Color(0xFFFFFBF0);
const _kBorder = BorderSide(color: Colors.black, width: 3);
const _kShadow = BoxShadow(color: Colors.black, offset: Offset(5, 5), blurRadius: 0);
const _kShadowSm = BoxShadow(color: Colors.black, offset: Offset(4, 4), blurRadius: 0);

// ─── Reusable widgets ───────────────────────────────────────────────────────

class _NeoButton extends StatelessWidget {
  final String label;
  final Color color;
  final VoidCallback onPressed;
  const _NeoButton({required this.label, required this.color, required this.onPressed});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onPressed,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 14),
        decoration: BoxDecoration(
          color: color,
          border: Border.all(color: Colors.black, width: 3),
          boxShadow: const [_kShadowSm],
        ),
        child: Text(
          label,
          style: const TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w900,
            color: Colors.black,
            letterSpacing: 1.5,
          ),
        ),
      ),
    );
  }
}

/// Chip-style tag (e.g. department, time)
class _NeoChip extends StatelessWidget {
  final String text;
  final Color color;
  const _NeoChip({required this.text, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: color,
        border: Border.all(color: Colors.black, width: 2),
        boxShadow: const [BoxShadow(color: Colors.black, offset: Offset(3, 3), blurRadius: 0)],
      ),
      child: Text(
        text,
        style: const TextStyle(
          fontSize: 13,
          fontWeight: FontWeight.w800,
          color: Colors.black,
        ),
      ),
    );
  }
}

/// Modal dialog built in neobrutalism style
class _NeoDialog extends StatelessWidget {
  final Color headerColor;
  final String headerText;
  final Widget body;
  final String buttonLabel;
  final VoidCallback onPressed;

  const _NeoDialog({
    required this.headerColor,
    required this.headerText,
    required this.body,
    required this.buttonLabel,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: Colors.transparent,
      elevation: 0,
      insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 40),
      child: Container(
        decoration: BoxDecoration(
          color: _kCream,
          border: Border.all(color: Colors.black, width: 3),
          boxShadow: const [BoxShadow(color: Colors.black, offset: Offset(7, 7), blurRadius: 0)],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header bar
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
              decoration: BoxDecoration(
                color: headerColor,
                border: const Border(bottom: _kBorder),
              ),
              child: Text(
                headerText,
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.w900,
                  color: Colors.black,
                  letterSpacing: 2,
                ),
              ),
            ),
            // Body
            Padding(
              padding: const EdgeInsets.all(20),
              child: body,
            ),
            // Footer button
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
              child: _NeoButton(
                label: buttonLabel,
                color: headerColor,
                onPressed: onPressed,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ─── Main screen ────────────────────────────────────────────────────────────

class CameraScreen extends StatefulWidget {
  final CameraDescription camera;
  const CameraScreen({super.key, required this.camera});

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> {
  late CameraController _controller;
  late Future<void> _initializeControllerFuture;
  bool _hasCaptured = false;
  bool _isProcessing = false;
  Position? _currentPosition;

  @override
  void initState() {
    super.initState();
    _controller = CameraController(widget.camera, ResolutionPreset.high);
    _initializeControllerFuture = _controller.initialize().then((_) async {
      await _getCurrentLocation();
      await Future.delayed(const Duration(seconds: 1));
      _autoCaptureImage();
    });
  }

  Future<void> _getCurrentLocation() async {
    try {
      bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) return;

      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
        if (permission == LocationPermission.denied) return;
      }
      if (permission == LocationPermission.deniedForever) return;

      _currentPosition = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
      );
    } catch (e) {
      debugPrint('Error getting location: $e');
    }
  }

  Future<void> _autoCaptureImage() async {
    if (_hasCaptured || _isProcessing) return;
    _hasCaptured = true;
    _isProcessing = true;

    try {
      if (mounted) {
        showDialog(
          context: context,
          barrierDismissible: false,
          builder: (_) => _buildScanningDialog(),
        );
      }

      final XFile file = await _controller.takePicture();

      if (kIsWeb) {
        await _sendImageToBackendWeb(file);
      } else {
        final path = join(
          (await getTemporaryDirectory()).path,
          '${DateTime.now().millisecondsSinceEpoch}.png',
        );
        await file.saveTo(path);
        await _sendImageToBackend(path);
      }
    } catch (e) {
      if (mounted) {
        Navigator.of(context).pop();
        _showErrorDialog('Error capturing image: $e');
      }
    } finally {
      _isProcessing = false;
    }
  }

  Future<void> _sendImageToBackendWeb(XFile imageFile) async {
    try {
      final url = Uri.parse(
          dotenv.env['FACE_RECOGNITION_WEB_URL'] ?? 'http://localhost:8080/api/attendance/clock-in-face');
      var request = http.MultipartRequest('POST', url);
      final bytes = await imageFile.readAsBytes();
      request.files.add(http.MultipartFile.fromBytes(
        'image',
        bytes,
        filename: '${DateTime.now().millisecondsSinceEpoch}.png',
      ));
      if (_currentPosition != null) {
        request.fields['latitude'] = _currentPosition!.latitude.toString();
        request.fields['longitude'] = _currentPosition!.longitude.toString();
      }
      var streamedResponse = await request.send().timeout(
        const Duration(seconds: 30),
        onTimeout: () => throw Exception('Connection timeout.'),
      );
      var response = await http.Response.fromStream(streamedResponse);
      if (mounted) Navigator.of(context).pop();

      if (response.statusCode == 200) {
        _handleRecognitionResponse(json.decode(response.body));
      } else {
        if (mounted) _showErrorDialog('Server error: ${response.statusCode}');
      }
    } catch (e) {
      if (mounted) {
        Navigator.of(context).pop();
        _showErrorDialog('Connection error: ${e.toString()}');
      }
    }
  }

  Future<void> _sendImageToBackend(String imagePath) async {
    try {
      final url = Uri.parse(
          dotenv.env['FACE_RECOGNITION_API_URL'] ?? 'http://10.0.2.2:8080/api/attendance/clock-in-face');
      var request = http.MultipartRequest('POST', url);
      request.files.add(await http.MultipartFile.fromPath('image', imagePath));
      if (_currentPosition != null) {
        request.fields['latitude'] = _currentPosition!.latitude.toString();
        request.fields['longitude'] = _currentPosition!.longitude.toString();
      }
      var streamedResponse = await request.send().timeout(
        const Duration(seconds: 30),
        onTimeout: () => throw Exception('Connection timeout.'),
      );
      var response = await http.Response.fromStream(streamedResponse);
      if (mounted) Navigator.of(context).pop();

      if (response.statusCode == 200) {
        _handleRecognitionResponse(json.decode(response.body));
      } else {
        if (mounted) _showErrorDialog('Server error: ${response.statusCode}');
      }
    } catch (e) {
      if (mounted) {
        Navigator.of(context).pop();
        _showErrorDialog('Connection error: ${e.toString()}');
      }
    }
  }

  void _handleRecognitionResponse(Map<String, dynamic> data) {
    // Handle error field
    if (data.containsKey('error')) {
      String msg = data['error'];
      if (msg.contains('No face detected')) {
        _showRetryDialog('NO FACE DETECTED', 'No face found in frame.\nPlease try again with better lighting.');
      } else {
        _showRetryDialog('ERROR', msg);
      }
      return;
    }

    final status = data['status'] ?? '';
    final message = data['message'] ?? '';
    final name = data['employee_name'] ?? 'Employee';

    // Backend returns status-based responses
    if (status == 'clocked_in') {
      _showWelcomeDialog(name, '', '', data);
    } else if (status == 'clocked_out') {
      _showGoodbyeDialog(name, '', '', data);
    } else if (status == 'too_soon') {
      _showRetryDialog('TOO SOON', message.isNotEmpty ? message : 'Please wait before clocking out.');
    } else if (status == 'face_mismatch') {
      _showRetryDialog('FACE MISMATCH', message.isNotEmpty ? message : 'Face does not match. Please try again.');
    } else if (status == 'not_identified') {
      _showRetryDialog('NOT RECOGNIZED', message.isNotEmpty ? message : 'Could not identify employee.');
    } else if (status == 'no_faces_registered') {
      _showRetryDialog('NO FACES', message.isNotEmpty ? message : 'No employee faces registered yet.');
    } else if (data.containsKey('results')) {
      // Legacy format support
      List<dynamic> results = data['results'] ?? [];
      if (results.isEmpty) {
        _showRetryDialog('NO FACE DETECTED', 'Position your face clearly in front of the camera.');
        return;
      }
      var r = results[0];
      if (r['recognized'] == true) {
        String rName = r['employee_name'];
        String action = r['action'];
        String dept = r['department'] ?? '';
        String pos = r['position'] ?? '';
        if (action == 'CHECK-IN') {
          _showWelcomeDialog(rName, dept, pos, r);
        } else if (action == 'CHECK-OUT') {
          _showGoodbyeDialog(rName, dept, pos, r);
        }
      } else {
        _showRetryDialog('NOT RECOGNIZED', 'Face not recognized.\nEnsure you are registered in the system.');
      }
    } else {
      _showRetryDialog('ERROR', message.isNotEmpty ? message : 'Unexpected response from server.');
    }
  }

  // ─── Dialog builders ───────────────────────────────────────────────────

  Widget _buildScanningDialog() {
    return Dialog(
      backgroundColor: Colors.transparent,
      elevation: 0,
      child: Container(
        padding: const EdgeInsets.all(28),
        decoration: BoxDecoration(
          color: _kCream,
          border: Border.all(color: Colors.black, width: 3),
          boxShadow: const [BoxShadow(color: Colors.black, offset: Offset(6, 6), blurRadius: 0)],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                color: _kYellow,
                border: Border.all(color: Colors.black, width: 3),
              ),
              child: const Padding(
                padding: EdgeInsets.all(12),
                child: CircularProgressIndicator(color: Colors.black, strokeWidth: 4),
              ),
            ),
            const SizedBox(height: 20),
            const Text(
              'SCANNING...',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w900,
                color: Colors.black,
                letterSpacing: 3,
              ),
            ),
            const SizedBox(height: 6),
            const Text(
              'Analyzing face data',
              style: TextStyle(fontSize: 13, color: Colors.black54, fontWeight: FontWeight.w600),
            ),
          ],
        ),
      ),
    );
  }

  void _showWelcomeDialog(String name, String dept, String pos, Map<String, dynamic> data) {
    showDialog(
      context: context,
      builder: (_) => _NeoDialog(
        headerColor: _kTeal,
        headerText: '✓  CHECK-IN',
        body: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              name.toUpperCase(),
              style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: Colors.black),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                if (dept.isNotEmpty) _NeoChip(text: dept, color: Colors.white),
                if (pos.isNotEmpty) _NeoChip(text: pos, color: _kYellow),
              ],
            ),
            const SizedBox(height: 16),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: _kTeal,
                border: Border.all(color: Colors.black, width: 2),
                boxShadow: const [BoxShadow(color: Colors.black, offset: Offset(3, 3), blurRadius: 0)],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('CHECK-IN TIME', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, letterSpacing: 1.5)),
                  const SizedBox(height: 4),
                  Text(
                    _formatTime(data['clock_in'] ?? data['check_in']),
                    style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w900, color: Colors.black),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),
            const Text(
              'Have a great day at work!',
              style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: Colors.black54),
            ),
          ],
        ),
        buttonLabel: 'OK  →',
        onPressed: () {
          Navigator.of(context).pop();
          _resetCapture();
        },
      ),
    );
  }

  void _showGoodbyeDialog(String name, String dept, String pos, Map<String, dynamic> data) {
    double workHours = (data['work_hours'] ?? 0.0).toDouble();
    double overtimeHours = (data['overtime_hours'] ?? 0.0).toDouble();

    showDialog(
      context: context,
      builder: (_) => _NeoDialog(
        headerColor: _kCoral,
        headerText: '✓  CHECK-OUT',
        body: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              name.toUpperCase(),
              style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: Colors.black),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                if (dept.isNotEmpty) _NeoChip(text: dept, color: Colors.white),
                if (pos.isNotEmpty) _NeoChip(text: pos, color: _kYellow),
              ],
            ),
            const SizedBox(height: 16),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: _kCoral,
                border: Border.all(color: Colors.black, width: 2),
                boxShadow: const [BoxShadow(color: Colors.black, offset: Offset(3, 3), blurRadius: 0)],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('CHECK-OUT TIME', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, letterSpacing: 1.5)),
                  const SizedBox(height: 4),
                  Text(
                    _formatTime(data['clock_out'] ?? data['check_out']),
                    style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w900, color: Colors.black),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: _kTeal,
                border: Border.all(color: Colors.black, width: 2),
                boxShadow: const [BoxShadow(color: Colors.black, offset: Offset(3, 3), blurRadius: 0)],
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('WORK HOURS', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, letterSpacing: 1.5)),
                      const SizedBox(height: 4),
                      Text(
                        '${workHours.toStringAsFixed(1)} hrs',
                        style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: Colors.black),
                      ),
                    ],
                  ),
                  if (overtimeHours > 0)
                    _NeoChip(
                      text: '+${overtimeHours.toStringAsFixed(1)} OT',
                      color: _kYellow,
                    ),
                ],
              ),
            ),
            // Day type & pay rate indicator
            if (data['day_type'] == 'holiday' || data['day_type'] == 'sunday')
              Padding(
                padding: const EdgeInsets.only(top: 12),
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: _kYellow,
                    border: Border.all(color: Colors.black, width: 2),
                  ),
                  child: Text(
                    '⭐ ${(data['day_type'] ?? '').toString().toUpperCase()} — ALL HOURS AT 2× PAY',
                    style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w900),
                    textAlign: TextAlign.center,
                  ),
                ),
              ),
            if (data['day_type'] == 'saturday')
              Padding(
                padding: const EdgeInsets.only(top: 12),
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: _kYellow,
                    border: Border.all(color: Colors.black, width: 2),
                  ),
                  child: Text(
                    '⭐ SATURDAY — OT AT 1.5× AFTER 8HRS',
                    style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w900),
                    textAlign: TextAlign.center,
                  ),
                ),
              ),
            const SizedBox(height: 14),
            Text(
              data['message'] ?? 'Thank you for your hard work today!',
              style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: Colors.black54),
            ),
          ],
        ),
        buttonLabel: 'OK  →',
        onPressed: () {
          Navigator.of(context).pop();
          _resetCapture();
        },
      ),
    );
  }

  void _showRetryDialog(String title, String message) {
    showDialog(
      context: context,
      builder: (_) => _NeoDialog(
        headerColor: _kCoral,
        headerText: '✕  $title',
        body: Text(
          message,
          style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: Colors.black, height: 1.5),
        ),
        buttonLabel: 'TRY AGAIN  →',
        onPressed: () {
          Navigator.of(context).pop();
          _resetCapture();
        },
      ),
    );
  }

  void _showErrorDialog(String message) {
    showDialog(
      context: context,
      builder: (_) => _NeoDialog(
        headerColor: _kCoral,
        headerText: '✕  ERROR',
        body: Text(
          message,
          style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: Colors.black, height: 1.5),
        ),
        buttonLabel: 'TRY AGAIN  →',
        onPressed: () {
          Navigator.of(context).pop();
          _resetCapture();
        },
      ),
    );
  }

  void _resetCapture() {
    setState(() {
      _hasCaptured = false;
      _isProcessing = false;
    });
    Future.delayed(const Duration(seconds: 1), () async {
      if (mounted) {
        await _getCurrentLocation();
        _autoCaptureImage();
      }
    });
  }

  String _formatTime(String? timestamp) {
    if (timestamp == null) return '--:--';
    try {
      DateTime dt = DateTime.parse(timestamp);
      return '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}:${dt.second.toString().padLeft(2, '0')}';
    } catch (e) {
      return timestamp;
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      // ── Neo AppBar ──────────────────────────────────────────────────────
      appBar: PreferredSize(
        preferredSize: const Size.fromHeight(56),
        child: Container(
          decoration: const BoxDecoration(
            color: _kYellow,
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
                    child: const Icon(Icons.fingerprint, color: _kYellow, size: 20),
                  ),
                  const SizedBox(width: 12),
                  const Expanded(
                    child: Text(
                      'HR ATTENDANCE',
                      style: TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.w900,
                        color: Colors.black,
                        letterSpacing: 2,
                      ),
                    ),
                  ),
                  // Live clock chip
                  _StreamClock(),
                ],
              ),
            ),
          ),
        ),
      ),

      // ── Camera body ─────────────────────────────────────────────────────
      body: FutureBuilder<void>(
        future: _initializeControllerFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.done) {
            return Stack(
              fit: StackFit.expand,
              children: [
                // Camera preview fills screen
                CameraPreview(_controller),

                // Dark overlay vignette
                Container(
                  decoration: const BoxDecoration(
                    gradient: RadialGradient(
                      center: Alignment.center,
                      radius: 0.85,
                      colors: [Colors.transparent, Color(0xAA000000)],
                    ),
                  ),
                ),

                // ── Scan frame overlay ─────────────────────────────────
                Center(
                  child: SizedBox(
                    width: 260,
                    height: 260,
                    child: Stack(
                      children: [
                        // Main frame
                        Container(
                          decoration: BoxDecoration(
                            border: Border.all(color: Colors.white, width: 2),
                          ),
                        ),
                        // Corner accents — TL
                        Positioned(top: 0, left: 0, child: _CornerAccent(topLeft: true)),
                        // Corner accents — TR
                        Positioned(top: 0, right: 0, child: _CornerAccent(topRight: true)),
                        // Corner accents — BL
                        Positioned(bottom: 0, left: 0, child: _CornerAccent(bottomLeft: true)),
                        // Corner accents — BR
                        Positioned(bottom: 0, right: 0, child: _CornerAccent(bottomRight: true)),
                      ],
                    ),
                  ),
                ),

                // ── Bottom instruction card ────────────────────────────
                Positioned(
                  bottom: 28,
                  left: 24,
                  right: 24,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                    decoration: BoxDecoration(
                      color: _kCream,
                      border: Border.all(color: Colors.black, width: 3),
                      boxShadow: const [BoxShadow(color: Colors.black, offset: Offset(5, 5), blurRadius: 0)],
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Container(
                          width: 28,
                          height: 28,
                          color: _kYellow,
                          child: const Icon(Icons.face_retouching_natural, size: 18, color: Colors.black),
                        ),
                        const SizedBox(width: 12),
                        const Text(
                          'LOOK AT THE CAMERA',
                          style: TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.w900,
                            color: Colors.black,
                            letterSpacing: 1.5,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),

                // ── Top-left status badge ──────────────────────────────
                Positioned(
                  top: 16,
                  left: 20,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: _kYellow,
                      border: Border.all(color: Colors.black, width: 2),
                      boxShadow: const [BoxShadow(color: Colors.black, offset: Offset(3, 3), blurRadius: 0)],
                    ),
                    child: Row(
                      children: [
                        Container(width: 8, height: 8, color: Colors.green),
                        const SizedBox(width: 6),
                        const Text(
                          'LIVE',
                          style: TextStyle(fontSize: 12, fontWeight: FontWeight.w900, letterSpacing: 2),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            );
          } else {
            // Loading state
            return Container(
              color: _kCream,
              child: Stack(
                children: [
                  const _NeoBalls(),
                  Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          width: 80,
                          height: 80,
                          decoration: BoxDecoration(
                            color: _kYellow,
                            border: Border.all(color: Colors.black, width: 3),
                            boxShadow: const [_kShadow],
                          ),
                          child: const Padding(
                            padding: EdgeInsets.all(16),
                            child: CircularProgressIndicator(color: Colors.black, strokeWidth: 4),
                          ),
                        ),
                        const SizedBox(height: 20),
                        const Text(
                          'INITIALIZING CAMERA',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w900,
                            color: Colors.black,
                            letterSpacing: 2,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            );
          }
        },
      ),
    );
  }
}

// ─── Decorative background balls ─────────────────────────────────────────────
class _NeoBalls extends StatelessWidget {
  const _NeoBalls();

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Positioned(
          top: -30,
          right: -20,
          child: _ball(100, _kYellow),
        ),
        Positioned(
          top: 120,
          left: -35,
          child: _ball(70, _kTeal),
        ),
        Positioned(
          bottom: 180,
          right: -25,
          child: _ball(60, _kCoral),
        ),
        Positioned(
          bottom: -20,
          left: 40,
          child: _ball(80, _kYellow),
        ),
        Positioned(
          top: 280,
          right: 30,
          child: _ball(40, _kTeal),
        ),
        Positioned(
          bottom: 80,
          right: 100,
          child: _ball(35, _kCoral),
        ),
        Positioned(
          top: 60,
          left: 80,
          child: _ball(25, Colors.white),
        ),
      ],
    );
  }

  Widget _ball(double size, Color color) {
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
}

// ─── Corner accent mark ──────────────────────────────────────────────────────
class _CornerAccent extends StatelessWidget {
  final bool topLeft;
  final bool topRight;
  final bool bottomLeft;
  final bool bottomRight;

  const _CornerAccent({
    this.topLeft = false,
    this.topRight = false,
    this.bottomLeft = false,
    this.bottomRight = false,
  });

  @override
  Widget build(BuildContext context) {
    const c = Color(0xFFFFEE32);
    const w = 24.0;
    const t = 4.0;

    return SizedBox(
      width: w,
      height: w,
      child: CustomPaint(
        painter: _CornerPainter(
          color: c,
          thickness: t,
          topLeft: topLeft,
          topRight: topRight,
          bottomLeft: bottomLeft,
          bottomRight: bottomRight,
        ),
      ),
    );
  }
}

class _CornerPainter extends CustomPainter {
  final Color color;
  final double thickness;
  final bool topLeft, topRight, bottomLeft, bottomRight;

  _CornerPainter({
    required this.color,
    required this.thickness,
    this.topLeft = false,
    this.topRight = false,
    this.bottomLeft = false,
    this.bottomRight = false,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..strokeWidth = thickness
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.square;

    const len = 20.0;

    if (topLeft) {
      canvas.drawLine(const Offset(0, 0), const Offset(len, 0), paint);
      canvas.drawLine(const Offset(0, 0), const Offset(0, len), paint);
    }
    if (topRight) {
      canvas.drawLine(Offset(size.width, 0), Offset(size.width - len, 0), paint);
      canvas.drawLine(Offset(size.width, 0), Offset(size.width, len), paint);
    }
    if (bottomLeft) {
      canvas.drawLine(Offset(0, size.height), Offset(len, size.height), paint);
      canvas.drawLine(Offset(0, size.height), Offset(0, size.height - len), paint);
    }
    if (bottomRight) {
      canvas.drawLine(Offset(size.width, size.height), Offset(size.width - len, size.height), paint);
      canvas.drawLine(Offset(size.width, size.height), Offset(size.width, size.height - len), paint);
    }
  }

  @override
  bool shouldRepaint(_CornerPainter old) => false;
}

// ─── Live clock widget ───────────────────────────────────────────────────────
class _StreamClock extends StatefulWidget {
  @override
  State<_StreamClock> createState() => _StreamClockState();
}

class _StreamClockState extends State<_StreamClock> {
  late String _time;

  @override
  void initState() {
    super.initState();
    _time = _now();
    _tick();
  }

  String _now() {
    final t = DateTime.now();
    return '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';
  }

  void _tick() {
    Future.delayed(const Duration(seconds: 30), () {
      if (mounted) {
        setState(() => _time = _now());
        _tick();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: Colors.black,
        border: Border.all(color: Colors.black, width: 2),
      ),
      child: Text(
        _time,
        style: const TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w900,
          color: Color(0xFFFFEE32),
          letterSpacing: 2,
        ),
      ),
    );
  }
}
