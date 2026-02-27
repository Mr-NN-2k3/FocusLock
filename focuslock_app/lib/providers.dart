import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'api_service.dart';

final statusProvider = StateNotifierProvider<StatusNotifier, Map<String, dynamic>>((ref) {
  final notifier = StatusNotifier();
  return notifier;
});

class StatusNotifier extends StateNotifier<Map<String, dynamic>> {
  Timer? _timer;

  StatusNotifier() : super({'active': false}) {
    _startPolling();
  }

  void _startPolling() {
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) async {
      final status = await ApiService.getStatus();
      state = status;
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }
}
