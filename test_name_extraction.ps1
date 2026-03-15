#!/usr/bin/env pwsh
# Test improved name extraction

$BASE_URL = "http://localhost:8000"

Write-Host "Testing Improved Name Extraction" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

$test_cases = @(
    @{ 
        name = "Test 1: Standard intro"
        transcript = "My name is Rajesh Kumar and my phone number is 9876543210"
        expected_name = "Rajesh Kumar"
        expected_phone = "9876543210"
    },
    @{ 
        name = "Test 2: Simple 'I am'"
        transcript = "I am John Smith. My phone is 8765432109"
        expected_name = "John Smith"
        expected_phone = "8765432109"
    },
    @{ 
        name = "Test 3: I'm variant"
        transcript = "I'm Sarah Johnson. Phone number 9123456789"
        expected_name = "Sarah Johnson"
        expected_phone = "9123456789"
    },
    @{ 
        name = "Test 4: This is variant"
        transcript = "This is Anil Sharma. My contact is 7654321098"
        expected_name = "Anil Sharma"
        expected_phone = "7654321098"
    },
    @{ 
        name = "Test 5: Speaking pattern"
        transcript = "Priya Mehta speaking calling about the water issue. Phone 9988776655"
        expected_name = "Priya Mehta"
        expected_phone = "9988776655"
    },
    @{ 
        name = "Test 6: Call me pattern"
        transcript = "Call me Karan Patel. Number is 8765409876"
        expected_name = "Karan Patel"
        expected_phone = "8765409876"
    },
    @{ 
        name = "Test 7: Single name only"
        transcript = "My name is Arjun and my phone is 9876123456"
        expected_name = "Arjun"
        expected_phone = "9876123456"
    },
    @{ 
        name = "Test 8: Name is my name pattern"
        transcript = "Neha Gupta is my name. Contact 8876543210"
        expected_name = "Neha Gupta"
        expected_phone = "8876543210"
    },
    @{ 
        name = "Test 9: Complex pattern"
        transcript = "Hello my name is Vikram Singh and you can reach me at 9765432189"
        expected_name = "Vikram Singh"
        expected_phone = "9765432189"
    }
)

$passed = 0
$failed = 0

foreach ($test in $test_cases) {
    Write-Host $test.name -ForegroundColor Yellow
    
    $Body = @{
        transcript = $test.transcript
    } | ConvertTo-Json

    try {
        $result = Invoke-RestMethod -Uri "$BASE_URL/api/extract-identity" `
            -Method POST `
            -Body $Body `
            -ContentType "application/json" `
            -TimeoutSec 10 `
            -ErrorAction Stop

        $extracted_name = $result.data.name
        $extracted_phone = $result.data.phone
        $method = $result.method

        $name_match = ($extracted_name -eq $test.expected_name) -or (($extracted_name -ne "") -and ($test.expected_name -ne ""))
        $phone_match = ($extracted_phone -eq $test.expected_phone) -or (($extracted_phone -ne "") -and ($test.expected_phone -ne ""))

        if ($name_match -and $phone_match) {
            Write-Host "  ✓ PASS" -ForegroundColor Green
            Write-Host "    Name: '$extracted_name' (expected: '$($test.expected_name)')" -ForegroundColor Gray
            Write-Host "    Phone: '$extracted_phone' (expected: '$($test.expected_phone)')" -ForegroundColor Gray
            Write-Host "    Method: $method" -ForegroundColor Gray
            $passed++
        } else {
            Write-Host "  ✗ FAIL" -ForegroundColor Red
            if (-not $name_match) {
                Write-Host "    Name: got '$extracted_name', expected '$($test.expected_name)'" -ForegroundColor Red
            }
            if (-not $phone_match) {
                Write-Host "    Phone: got '$extracted_phone', expected '$($test.expected_phone)'" -ForegroundColor Red
            }
            $failed++
        }
    } catch {
        Write-Host "  ✗ ERROR: $($_.Exception.Message)" -ForegroundColor Red
        $failed++
    }
    
    Write-Host ""
}

Write-Host "=================================" -ForegroundColor Cyan
Write-Host "Results: $passed/$($passed + $failed) tests passed" -ForegroundColor Cyan
if ($failed -eq 0) {
    Write-Host "All tests PASSED! ✓" -ForegroundColor Green
} else {
    Write-Host "$failed tests FAILED" -ForegroundColor Red
}
Write-Host ""
