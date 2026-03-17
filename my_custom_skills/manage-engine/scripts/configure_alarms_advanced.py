#!/usr/bin/env python3
"""
Configure Alarms Advanced Script
Demonstrates comprehensive usage of ManageEngine Configure Alarms API
"""

import sys
import json
import logging
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def example_1_simple_threshold_template(client, resource_id):
    """
    Example 1: Apply existing threshold template to a monitor
    (Simplest and recommended approach)
    """
    logger.info("=" * 60)
    logger.info("Example 1: Apply Existing Threshold Template")
    logger.info("=" * 60)

    result = client.configure_alarm(
        resource_id=resource_id,
        attribute_id="708",  # CPU Utilization
        threshold_id="1",    # Default threshold profile
        request_type=1,
        override_conf=True
    )

    logger.info(f"Result: {result}")
    return result


def example_2_with_actions(client, resource_id, action_id):
    """
    Example 2: Configure alarm with action notifications
    """
    logger.info("\n" + "=" * 60)
    logger.info("Example 2: Configure Alarm with Actions")
    logger.info("=" * 60)

    result = client.configure_alarm(
        resource_id=resource_id,
        attribute_id="708",
        threshold_id="3",
        critical_action_id=action_id,
        warning_action_id=action_id,
        clear_action_id=action_id,
        availability_critical_poll_count=4,
        availability_clear_poll_count=7,
        request_type=1,
        override_conf=True
    )

    logger.info(f"Result: {result}")
    return result


def example_3_multiple_attributes(client, resource_id):
    """
    Example 3: Configure alarms for multiple attributes at once
    """
    logger.info("\n" + "=" * 60)
    logger.info("Example 3: Multiple Attributes Configuration")
    logger.info("=" * 60)

    # Configure CPU, Memory, and Disk in one call
    result = client.configure_alarm(
        resource_id=resource_id,
        attribute_id="708,685,711",  # CPU, Memory, Disk
        threshold_id="1",
        request_type=1,
        override_conf=True
    )

    logger.info(f"Result: {result}")
    return result


def example_4_custom_thresholds(client, resource_id):
    """
    Example 4: Configure custom threshold values
    """
    logger.info("\n" + "=" * 60)
    logger.info("Example 4: Custom Threshold Values")
    logger.info("=" * 60)

    result = client.configure_alarm(
        resource_id=resource_id,
        attribute_id="708",
        critical_threshold=95,
        warning_threshold=85,
        info_threshold=70,
        critical_condition=">",
        warning_condition=">",
        info_condition="<",
        consecutive_critical_polls=3,
        consecutive_warning_polls=2,
        consecutive_clear_polls=1,
        critical_message="CPU usage critically high - immediate action required!",
        warning_message="CPU usage elevated - monitor closely",
        info_message="CPU usage returned to normal",
        request_type=1,
        override_conf=True
    )

    logger.info(f"Result: {result}")
    return result


def example_5_monitor_type_template(client, resource_type):
    """
    Example 5: Apply threshold template to all monitors of a specific type
    """
    logger.info("\n" + "=" * 60)
    logger.info("Example 5: Monitor Type Template Application")
    logger.info("=" * 60)

    result = client.configure_alarm(
        resource_type=resource_type,  # e.g., "servers", "PHP", "MySQL"
        attribute_id="708",
        threshold_id="1",
        request_type=1,
        override_conf=False  # Don't override existing configurations
    )

    logger.info(f"Result: {result}")
    return result


def example_6_remove_configuration(client, resource_id):
    """
    Example 6: Remove alarm configuration
    """
    logger.info("\n" + "=" * 60)
    logger.info("Example 6: Remove Alarm Configuration")
    logger.info("=" * 60)

    result = client.configure_alarm(
        resource_id=resource_id,
        attribute_id="708",
        request_type=3  # Remove configuration
    )

    logger.info(f"Result: {result}")
    return result


def example_7_availability_alarm(client, resource_id, action_id):
    """
    Example 7: Configure availability (server down) alarm
    """
    logger.info("\n" + "=" * 60)
    logger.info("Example 7: Availability Alarm Configuration")
    logger.info("=" * 60)

    result = client.configure_alarm(
        resource_id=resource_id,
        attribute_id="700",  # Availability attribute
        threshold_id="1",
        critical_action_id=action_id,
        availability_critical_poll_count=3,  # Alert after 3 consecutive failures
        availability_clear_poll_count=2,     # Clear after 2 consecutive successes
        request_type=1,
        override_conf=True
    )

    logger.info(f"Result: {result}")
    return result


def example_8_health_status_alarm(client, resource_id, action_id):
    """
    Example 8: Configure health status alarm
    """
    logger.info("\n" + "=" * 60)
    logger.info("Example 8: Health Status Alarm Configuration")
    logger.info("=" * 60)

    result = client.configure_alarm(
        resource_id=resource_id,
        attribute_id="701",  # Health Status attribute
        threshold_id="1",
        critical_action_id=action_id,
        request_type=1,
        override_conf=True
    )

    logger.info(f"Result: {result}")
    return result


def example_9_memory_disk_alarms(client, resource_id):
    """
    Example 9: Configure Memory and Disk alarms with custom thresholds
    """
    logger.info("\n" + "=" * 60)
    logger.info("Example 9: Memory and Disk Alarms")
    logger.info("=" * 60)

    # Memory alarm
    logger.info("Configuring Memory alarm...")
    memory_result = client.configure_alarm(
        resource_id=resource_id,
        attribute_id="685",  # Memory Utilization
        critical_threshold=90,
        warning_threshold=80,
        request_type=1,
        override_conf=True
    )

    # Disk alarm
    logger.info("Configuring Disk alarm...")
    disk_result = client.configure_alarm(
        resource_id=resource_id,
        attribute_id="711",  # Disk Utilization
        critical_threshold=95,
        warning_threshold=85,
        request_type=1,
        override_conf=True
    )

    logger.info(f"Memory Result: {memory_result}")
    logger.info(f"Disk Result: {disk_result}")
    return memory_result, disk_result


def example_10_comprehensive_setup(client, resource_id, action_id):
    """
    Example 10: Comprehensive alarm setup for a server
    Configures: Availability, Health, CPU, Memory, Disk
    """
    logger.info("\n" + "=" * 60)
    logger.info("Example 10: Comprehensive Alarm Setup")
    logger.info("=" * 60)

    alarms = {
        "Availability": {
            "attribute_id": "700",
            "threshold_id": "1",
            "critical_action_id": action_id,
            "availability_critical_poll_count": 3,
            "availability_clear_poll_count": 2
        },
        "Health Status": {
            "attribute_id": "701",
            "threshold_id": "1",
            "critical_action_id": action_id
        },
        "CPU Utilization": {
            "attribute_id": "708",
            "critical_threshold": 90,
            "warning_threshold": 80,
            "critical_action_id": action_id,
            "consecutive_critical_polls": 3,
            "consecutive_warning_polls": 2
        },
        "Memory Utilization": {
            "attribute_id": "685",
            "critical_threshold": 90,
            "warning_threshold": 80,
            "critical_action_id": action_id
        },
        "Disk Utilization": {
            "attribute_id": "711",
            "critical_threshold": 95,
            "warning_threshold": 85,
            "critical_action_id": action_id
        }
    }

    results = {}
    for alarm_name, params in alarms.items():
        logger.info(f"\nConfiguring {alarm_name}...")
        result = client.configure_alarm(
            resource_id=resource_id,
            request_type=1,
            override_conf=True,
            **params
        )
        results[alarm_name] = result
        logger.info(f"{alarm_name}: {'Success' if result else 'Failed'}")

    return results


def print_usage():
    """Print usage instructions"""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║          ManageEngine Configure Alarms API - Advanced Examples               ║
╚══════════════════════════════════════════════════════════════════════════════╝

Usage:
    python configure_alarms_advanced.py <example_number> <resource_id> [action_id]

Examples:
    1  - Apply existing threshold template (simple)
    2  - Configure alarm with action notifications
    3  - Configure multiple attributes at once
    4  - Configure custom threshold values
    5  - Apply template to monitor type
    6  - Remove alarm configuration
    7  - Configure availability alarm
    8  - Configure health status alarm
    9  - Configure memory and disk alarms
    10 - Comprehensive setup (all alarms)

Parameters:
    example_number : Number of example to run (1-10)
    resource_id    : Resource ID of the monitor
    action_id      : Action ID for notifications (required for examples 2, 7, 8, 10)

Example Commands:
    # Simple threshold template
    python configure_alarms_advanced.py 1 10113263

    # With action notifications
    python configure_alarms_advanced.py 2 10113263 10000003

    # Multiple attributes
    python configure_alarms_advanced.py 3 10113263

    # Custom thresholds
    python configure_alarms_advanced.py 4 10113263

    # Monitor type template
    python configure_alarms_advanced.py 5 servers

    # Comprehensive setup
    python configure_alarms_advanced.py 10 10113263 10000003

Common Attribute IDs:
    700 - Availability (Server Up/Down)
    701 - Health Status
    708 - CPU Utilization
    685 - Memory Utilization
    711 - Disk Utilization

Common Request Types:
    1 - Save
    2 - Save and Configure Another
    3 - Remove Configuration
    8 - Delete Template
    """)


def main():
    if len(sys.argv) < 3:
        print_usage()
        sys.exit(1)

    example_num = sys.argv[1]
    resource_id = sys.argv[2]
    action_id = sys.argv[3] if len(sys.argv) > 3 else None

    # Initialize client
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)

    logger.info(f"Using ManageEngine server: {DEFAULT_URL}")
    logger.info(f"Resource ID: {resource_id}")
    if action_id:
        logger.info(f"Action ID: {action_id}")

    # Run selected example
    examples = {
        "1": lambda: example_1_simple_threshold_template(client, resource_id),
        "2": lambda: example_2_with_actions(client, resource_id, action_id),
        "3": lambda: example_3_multiple_attributes(client, resource_id),
        "4": lambda: example_4_custom_thresholds(client, resource_id),
        "5": lambda: example_5_monitor_type_template(client, resource_id),
        "6": lambda: example_6_remove_configuration(client, resource_id),
        "7": lambda: example_7_availability_alarm(client, resource_id, action_id),
        "8": lambda: example_8_health_status_alarm(client, resource_id, action_id),
        "9": lambda: example_9_memory_disk_alarms(client, resource_id),
        "10": lambda: example_10_comprehensive_setup(client, resource_id, action_id),
    }

    if example_num not in examples:
        logger.error(f"Invalid example number: {example_num}")
        print_usage()
        sys.exit(1)

    # Check action_id requirement
    requires_action = ["2", "7", "8", "10"]
    if example_num in requires_action and not action_id:
        logger.error(f"Example {example_num} requires action_id parameter")
        print_usage()
        sys.exit(1)

    try:
        result = examples[example_num]()
        logger.info("\n" + "=" * 60)
        logger.info("✓ Example completed successfully!")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"Error running example: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
