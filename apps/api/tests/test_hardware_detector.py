from app.application.services.hardware_detector import HardwareDetector


def test_hardware_detector_returns_available_capabilities_without_gpu():
    detector = HardwareDetector(
        memory_provider=lambda: (32_000, 12_000),
        command_locator=lambda command: None,
        cpu_count_provider=lambda: 8,
        system_provider=lambda: "Linux",
        machine_provider=lambda: "x86_64",
        processor_provider=lambda: "Test CPU",
        python_version_provider=lambda: "3.9.0",
    )

    profile = detector.detect()

    assert profile.cpu_name == "Test CPU"
    assert profile.cpu_cores == 8
    assert profile.total_memory_bytes == 32_000
    assert profile.available_memory_bytes == 12_000
    assert profile.cuda_available is False
    assert profile.mps_available is False
    assert profile.directml_available is False


def test_hardware_detector_detects_cuda_and_apple_mps():
    cuda_detector = HardwareDetector(
        memory_provider=lambda: (1, 1),
        command_locator=lambda command: "/usr/bin/nvidia-smi",
        cpu_count_provider=lambda: 1,
        system_provider=lambda: "Linux",
        machine_provider=lambda: "x86_64",
        processor_provider=lambda: "CPU",
        python_version_provider=lambda: "3.9.0",
    )
    mps_detector = HardwareDetector(
        memory_provider=lambda: (1, 1),
        command_locator=lambda command: None,
        cpu_count_provider=lambda: 1,
        system_provider=lambda: "Darwin",
        machine_provider=lambda: "arm64",
        processor_provider=lambda: "CPU",
        python_version_provider=lambda: "3.9.0",
    )

    assert cuda_detector.detect().cuda_available is True
    assert mps_detector.detect().mps_available is True
