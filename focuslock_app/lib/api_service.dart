import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  static const String baseUrl = 'http://127.0.0.1:5000/api';

  static Future<Map<String, dynamic>> getStatus() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/status')).timeout(const Duration(seconds: 2));
      return jsonDecode(response.body);
    } catch (e) {
      return {'error': e.toString()};
    }
  }

  static Future<bool> startSession({
    required int duration,
    required String mode,
    required String intent,
    required List<String> whitelist,
    required List<String> blacklist,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/start'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'duration': duration,
          'mode': mode,
          'intent': intent,
          'whitelist': whitelist.join(','),
          'blacklist': blacklist.join(','),
        }),
      );
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  static Future<bool> stopSession() async {
    try {
      final response = await http.post(Uri.parse('$baseUrl/stop'));
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  static Future<bool> continueSession(int additionalMinutes) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/continue'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'duration': additionalMinutes}),
      );
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }
}
