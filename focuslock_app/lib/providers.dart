import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'api_service.dart';

class StatusNotifier extends Notifier<Map<String, dynamic>> {
  Timer? _timer;

  @override
  Map<String, dynamic> build() {
    _startPolling();
    ref.onDispose(() {
      _timer?.cancel();
    });
    return {'active': false};
  }

  void _startPolling() {
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) async {
      final status = await ApiService.getStatus();
      if (!status.containsKey('error')) {
        state = status;
      }
    });
  }
}

final statusProvider = NotifierProvider<StatusNotifier, Map<String, dynamic>>(StatusNotifier.new);
