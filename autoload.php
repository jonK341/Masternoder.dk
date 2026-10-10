<?php
// autoload.php

// Check if Composer's autoload file exists
if (file_exists(__DIR__ . '/vendor/autoload.php')) {
    require __DIR__ . '/vendor/autoload.php'; // Adjust the path if necessary
} else {
    die("Autoload file not found. Please run 'composer install'.");
}
?>